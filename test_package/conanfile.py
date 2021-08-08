from conans import ConanFile, tools
import os

class MagnumTestConan(ConanFile):
    requires = "magnum-bindings/2020.06@camposs/stable"

    def test(self):
      # self.conanfile_directory
      self.run('{0} -c "from magnum import Vector2; print(Vector2(1.0, 2.0))"'.format(os.environ.get("PYTHON")))
