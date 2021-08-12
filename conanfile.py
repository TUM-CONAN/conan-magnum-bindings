#!/usr/bin/env python
# -*- coding: utf-8 -*-

from conans import ConanFile, CMake, tools
import os

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
    description =   "magnum-bindings — Lightweight and modular C++11/C++14 \
                    graphics middleware for games and data visualization"
    # topics can get used for searches, GitHub topics, Bintray tags etc. Add here keywords about the library
    topics = ("conan", "corrade", "graphics", "rendering", "3d", "2d", "opengl")
    url = "https://github.com/ulricheck/conan-magnum-bindings"
    homepage = "https://magnum.graphics"
    author = "ulrich eck (forked on github)"
    license = "MIT"  # Indicates license type of the packaged library; please use SPDX Identifiers https://spdx.org/licenses/
    exports = ["LICENSE.md"]
    exports_sources = ["CMakeLists.txt", "patches/*"]
    generators = "cmake"
    short_paths = True  # Some folders go out of the 260 chars path length scope (windows)

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
        "magnum:with_sdl2application": True,
    }

    # Custom attributes for Bincrafters recipe conventions
    _source_subfolder = "source_subfolder"
    _build_subfolder = "build_subfolder"

    # we could make this more modular byu adding options ..
    requires = (
        "magnum/2020.06@camposs/stable",
        "nodejs_installer/[>=10.15.0]@bincrafters/stable",
    )

    def system_package_architecture(self):
        if tools.os_info.with_apt:
            if self.settings.arch == "x86":
                return ':i386'
            elif self.settings.arch == "x86_64":
                return ':amd64'
            elif self.settings.arch == "armv6" or self.settings.arch == "armv7":
                return ':armel'
            elif self.settings.arch == "armv7hf":
                return ':armhf'
            elif self.settings.arch == "armv8":
                return ':arm64'

        if tools.os_info.with_yum:
            if self.settings.arch == "x86":
                return '.i686'
            elif self.settings.arch == 'x86_64':
                return '.x86_64'
        return ""

    def system_requirements(self):
        # Install required dependent packages stuff on linux
        pass

    def build_requirements(self):
        pass

    def config_options(self):
        if self.settings.os == 'Windows':
            del self.options.fPIC

    def configure(self):

        # To fix issue with resource management, see here:
        # https://github.com/mosra/magnum/issues/304#issuecomment-451768389
        if self.options.shared:
            self.options['magnum'].add_option('shared', True)

        # if self.options.with_assimpimporter:
        #     self.options['magnum'].add_option('with_anyimageimporter', True)
        if self.options.with_python:
            self.options['magnum'].add_option('with_windowlesseglapplication', True)


    def requirements(self):
        self.requires("generators/1.0.0@camposs/stable")
        if self.options.with_python:
            self.requires("python_dev_config/[>=0.6]@camposs/stable")
            self.requires("pybind11/[2.7.1]@camposs/stable")


    def source(self):
        source_url = "https://github.com/mosra/magnum-bindings"
        tools.get("{0}/archive/v{1}.tar.gz".format(source_url, self.version))
        extracted_dir = self.name + "-" + self.version

        # Rename to "source_subfolder" is a convention to simplify later steps
        os.rename(extracted_dir, self._source_subfolder)

        if self.settings.os == "Macos":
            tools.replace_in_file(os.path.join(self._source_subfolder, "src", "python", "magnum", "CMakeLists.txt"),
                "list(APPEND magnum_LIBS Magnum::GlfwApplication)",
                """list(APPEND magnum_LIBS Magnum::GlfwApplication "-framework Cocoa -framework OpenGL")""")

    def _configure_cmake(self):
        cmake = CMake(self)

        def add_cmake_option(option, value):
            var_name = "{}".format(option).upper()
            value_str = "{}".format(value)
            var_value = "ON" if value_str == 'True' else "OFF" if value_str == 'False' else value_str 
            cmake.definitions[var_name] = var_value

        for option, value in self.options.items():
            add_cmake_option(option, value)

        # Magnum uses suffix on the resulting 'lib'-folder when running cmake.install()
        # Set it explicitly to empty, else Magnum might set it implicitly (eg. to "64")
        add_cmake_option("LIB_SUFFIX", "")

        add_cmake_option("BUILD_STATIC", not self.options.shared)
        add_cmake_option("BUILD_STATIC_PIC", not self.options.shared and self.options.get_safe("fPIC"))
        # add_cmake_option("IMGUI_DIR", os.path.join(self.deps_cpp_info["imgui"].rootpath, 'include'))

        if self.options.with_python:

            # some sensible defaults            
            python = None
            python_version = None
            if "PYTHON" in os.environ:
                python = os.environ.get("PYTHON")
                python_version = os.environ.get("PYTHON_VERSION")
   
            if python is None:
                python = self.deps_env_info["python_dev_config"].PYTHON
                python_version = self.deps_env_info["python_dev_config"].PYTHON_VERSION

            if not python:
                python = self.options["python_dev_config"].python
                python = tools.which(python)
                python_version = "3"

            self.output.info("python executable: %s (%s)" % (python, python_version))
            cmake.definitions['PYTHON_EXECUTABLE'] = python
            cmake.definitions['PYTHON_VERSION_STRING'] = python_version
            if self.settings.os == "Macos":
                cmake.definitions['CMAKE_FIND_FRAMEWORK'] = "LAST"

        cmake.configure(build_folder=self._build_subfolder)

        return cmake

    def build(self):

        source_dir = os.path.join(
            self.source_folder, self._source_subfolder)
        tools.patch(source_dir, "patches/patch_pybind2.6_commit1.diff")
        tools.patch(source_dir, "patches/patch_pybind2.6_commit2.diff")

        cmake = self._configure_cmake()
        cmake.build()

    def package(self):
        self.copy(pattern="LICENSE", dst="licenses", src=self._source_subfolder)

        cmake = self._configure_cmake()
        cmake.install()
        if self.options.with_python:
            # with tools.chdir(os.path.join(self._build_subfolder, self._source_subfolder, 'src', 'python')):
            #     self.run("{0} setup.py install".format(os.environ.get("PYTHON")))
            self.copy('*.py*', dst=os.path.join('lib', 'python'), src=os.path.join(self._source_subfolder, 'src', 'python'), keep_path=True)
            self.copy('*.so', dst=os.path.join('lib', 'python'), src=os.path.join(self._build_subfolder, 'lib'), keep_path=True)
            self.copy('*.pyd', dst=os.path.join('lib', 'python'), src=os.path.join(self._build_subfolder, 'lib'), keep_path=True)

    def package_info(self):
        if self.options.with_python:
            self.env_info.PYTHONPATH.append(os.path.join(self.package_folder,'lib', 'python'))
