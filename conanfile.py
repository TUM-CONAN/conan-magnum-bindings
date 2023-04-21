#!/usr/bin/env python
# -*- coding: utf-8 -*-

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout, CMakeDeps
from conan.tools.scm import Git
from conan.tools.files import load, update_conandata, copy, collect_libs, get, replace_in_file, patch, chdir, unzip
from conan.tools.microsoft.visual import check_min_vs
from conan.tools.system.package_manager import Apt
import os
import glob

def sort_libs(correct_order, libs, lib_suffix='', reverse_result=False):
    # Add suffix for correct string matching
    correct_order[:] = [s.__add__(lib_suffix) for s in correct_order]

    result = []
    for expectedLib in correct_order:
        for lib in libs:
            if expectedLib == lib:
                result.append(lib)

    if reverse_result:
        # Linking happens in reversed order
        result.reverse()

    return result

class LibnameConan(ConanFile):
    name = "magnum-bindings"
    version = "2020.06"
    description = "magnum-bindings — Lightweight and modular C++11/C++14 \
                    graphics middleware for games and data visualization"
    # topics can get used for searches, GitHub topics, Bintray tags etc. Add here keywords about the library
    topics = ("conan", "corrade", "graphics", "rendering", "3d", "2d", "opengl")
    url = "https://github.com/TUM-CONAN/conan-magnum-bindings"
    homepage = "https://magnum.graphics"
    author = "ulrich eck (forked on github)"
    license = "MIT"
    exports = ["LICENSE.md"]
    exports_sources = ["CMakeLists.txt", "patches/*"]

    # Options may need to change depending on the packaged library.
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False], 
        "fPIC": [True, False],
        "with_python": [True, False],
    }
    default_options = {
        "shared": False, 
        "fPIC": True,
        "with_python": True,
        "magnum/*:with_sdl2application": True,
        "magnum/*:build_plugins_static": False,
        "cpython/*:env_vars": True,
    }

    def config_options(self):
        if self.settings.os == 'Windows':
            del self.options.fPIC

    def configure(self):

        # To fix issue with resource management, see here:
        # https://github.com/mosra/magnum/issues/304#issuecomment-451768389
        if self.options.shared:
            self.options['magnum']['shared'] = True

        # if self.options.with_assimpimporter:
        #     self.options['magnum'].add_option('with_anyimageimporter', True)
        if self.options.with_python:
            self.options['magnum']['with_windowlesseglapplication'] = True

    def requirements(self):
        self.requires("magnum/2020.06@camposs/stable")

        if self.options.with_python:
            self.requires("cpython/3.10.0")
            self.requires("pybind11/2.10.1")

    def export(self):
        update_conandata(self, {"sources": {
            "commit": "v{}".format(self.version),
            "url": "https://github.com/mosra/magnum-bindings.git"
            }}
            )

    def source(self):
        git = Git(self)
        sources = self.conan_data["sources"]
        git.clone(url=sources["url"], target=self.source_folder)
        git.checkout(commit=sources["commit"])
        replace_in_file(self, os.path.join(self.source_folder, "CMakeLists.txt"),
            "find_package(Magnum REQUIRED)",
            "cmake_policy(SET CMP0074 NEW)\nfind_package(Magnum REQUIRED)")

        # if self.settings.os == "Macos":
        #     tools.replace_in_file(os.path.join(self._source_subfolder, "src", "python", "magnum", "CMakeLists.txt"),
        #         "list(APPEND magnum_LIBS Magnum::GlfwApplication)",
        #         """list(APPEND magnum_LIBS Magnum::GlfwApplication "-framework Cocoa -framework OpenGL")""")

    def generate(self):
        tc = CMakeToolchain(self)

        def add_cmake_option(option, value):
            var_name = "{}".format(option).upper()
            value_str = "{}".format(value)
            var_value = "ON" if value_str == 'True' else "OFF" if value_str == 'False' else value_str
            tc.variables[var_name] = var_value

        for option, value in self.options.items():
            add_cmake_option(option, value)

        # Corrade uses suffix on the resulting 'lib'-folder when running cmake.install()
        # Set it explicitly to empty, else Corrade might set it implicitly (eg. to "64")
        add_cmake_option("LIB_SUFFIX", "")

        add_cmake_option("BUILD_STATIC", not self.options.shared)
        add_cmake_option("BUILD_STATIC_PIC", not self.options.shared and self.options.get_safe("fPIC"))
        corrade_root = self.dependencies["corrade"].package_folder
        tc.variables["Corrade_ROOT"] = corrade_root
        magnum_root = self.dependencies["magnum"].package_folder
        tc.variables["Magnum_ROOT"] = magnum_root

        if self.options.with_python:
            python_version = self.dependencies["cpython"].ref.version
            python = self.dependencies["cpython"].env_vars.PYTHON
            self.output.info("python executable: %s (%s)" % (python, python_version))
            tc.preprocessor_definitions['PYTHON_EXECUTABLE'] = python
            tc.preprocessor_definitions['PYTHON_VERSION_STRING'] = python_version
            if self.settings.os == "Macos":
                tc.preprocessor_definitions['CMAKE_FIND_FRAMEWORK'] = "LAST"

        tc.generate()

        deps = CMakeDeps(self)
        deps.set_property("magnum", "cmake_find_mode", "none")
        deps.set_property("corrade", "cmake_find_mode", "none")
        deps.generate()

    def layout(self):
        cmake_layout(self, src_folder="source_subfolder")

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, pattern="LICENSE", dst="licenses", src=self.source_folder)
        cmake = CMake(self)
        cmake.install()

        if self.options.with_python:
            python_version = self.dependencies["cpython"].ref.version
            python = self.dependencies["cpython"].env_vars.PYTHON
            with chdir(self, os.path.join(self.build_folder, self.source_folder, 'src', 'python')):
                self.run("{0} setup.py install --prefix=\"{1}\"".format(python, self.package_folder))

            # somehow needed to enable importing the module ...
            pypath = glob.glob(os.path.join(self.package_folder, 'lib', 'python*'))[0]
            output_path = os.path.join(pypath, 'site-packages')
            with chdir(self, output_path):
                egg_files = glob.glob("*.egg")
                for egg in egg_files:
                    unzip(self, egg)
                    os.unlink(egg)

    # def build(self):
    #
    #     # if self.options.with_python:
    #     #     tools.replace_in_file(os.path.join(self._source_subfolder, 'src', 'python', 'setup.py.cmake'),
    #     #         "zip_safe=True", "zip_safe=False")
    #
    #     source_dir = os.path.join(
    #         self.source_folder, self._source_subfolder)
    #     tools.patch(source_dir, "patches/patch_pybind2.6_commit1.diff")
    #     tools.patch(source_dir, "patches/patch_pybind2.6_commit2.diff")
    #
    #     cmake = self._configure_cmake()
    #     cmake.build()

    # def package(self):
    #     self.copy(pattern="LICENSE", dst="licenses", src=self._source_subfolder)
    #
    #     cmake = self._configure_cmake()
    #     cmake.install()

    def package_info(self):
        if self.options.with_python:
            python_version = self.dependencies["cpython"].ref.version
            python = self.dependencies["cpython"].env_vars.PYTHON
            path = os.path.join(glob.glob(os.path.join(self.package_folder, 'lib', 'python*'))[0], 'site-packages')
            self.output.info("Append to PYTHONPATH: {0}".format(path))
            self.env_info.PYTHONPATH.append(path)
