import os

from conan import ConanFile
from conan.tools.build.cross_building import cross_building
from conan.tools.cmake import CMake
from conan.tools.layout import basic_layout


class TestPackageConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeToolchain", "CMakeDeps", "VirtualBuildEnv", "VirtualRunEnv"

    def layout(self):
        basic_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not cross_building(self):
            cmd = os.path.join(self.cpp.build.bindirs[0], "test_package")
            self.run(cmd, env="conanrun")
