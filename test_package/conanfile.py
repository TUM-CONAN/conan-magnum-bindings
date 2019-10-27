from conans import ConanFile, tools

class MagnumTestConan(ConanFile):
    requires = "magnum-bindings/2019.10@camposs/stable"

    def test(self):
      # self.conanfile_directory
      with tools.pythonpath(self):
          from magnum import Vector2
          print("A Magnum::Vector2: %s" % Vector2(1.0, 2.0))