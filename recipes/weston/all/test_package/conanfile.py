import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.env import VirtualBuildEnv
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain
from conan.tools.scm import Version


class TestPackageConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def layout(self):
        basic_layout(self)

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build_requirements(self):
        self.tool_requires("meson/1.3.2")
        if not self.conf.get("tools.gnu:pkg_config", default=False, check_type=str):
            self.tool_requires("pkgconf/2.1.0")

    def generate(self):
        virtual_build_env = VirtualBuildEnv(self)
        virtual_build_env.generate()
        tc = MesonToolchain(self)
        tc.project_options["weston_version"] = str(Version(self.dependencies.direct_host["weston"].ref.version).major)
        tc.generate()
        pkg_config_deps = PkgConfigDeps(self)
        pkg_config_deps.generate()

    def build(self):
        meson = Meson(self)
        meson.configure()
        meson.build()

    def test(self):
        if can_run(self):
            bin_path = os.path.join(self.cpp.build.bindir, "test_package")
            self.run(bin_path, env="conanrun")
