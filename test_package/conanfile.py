from conans import ConanFile, tools
import os

class MagnumTestConan(ConanFile):
    requires = "magnum-bindings/2020.06@camposs/stable"

    def test(self):
      # self.conanfile_directory

      # some sensible defaults            
      python = None
      if "PYTHON" in os.environ:
          python = os.environ.get("PYTHON")
          python = tools.which(python)

      if python is None:
          python = self.deps_env_info["python_dev_config"].PYTHON

      if not python:
          python = self.options["python_dev_config"].python

      self.run('{0} -c "from magnum import Vector2; print(Vector2(1.0, 2.0))"'.format(python))
