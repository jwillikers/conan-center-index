from conan import ConanFile
from conan.tools.build.cross_building import cross_building
from conan.tools.gnu.pkgconfig import PkgConfig
from conan.tools.layout import basic_layout


class TestPackageConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "PkgConfigDeps", "VirtualBuildEnv", "VirtualRunEnv"

    def layout(self):
        basic_layout(self)

    def build(self):
        pass

    def test(self):
        if not cross_building(self):
            pkg_config = PkgConfig(self, "wayland-scanner", self.generators_folder)
            self.run('%s --version' % pkg_config.variables["wayland_scanner"], env="conanrun")
