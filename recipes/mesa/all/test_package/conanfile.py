import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


class TestPackageConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "PkgConfigDeps", "VirtualRunEnv", "VirtualBuildEnv"
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
        tc = MesonToolchain(self)
        tc.project_options["egl"] = "enabled" if self.dependencies[self.tested_reference_str].options.get_safe("egl") and not self.settings.os == "Windows" else "disabled"
        tc.project_options["gbm"] = "enabled" if self.dependencies[self.tested_reference_str].options.get_safe("gbm") else "disabled"
        tc.project_options["glvnd"] = "enabled" if self.dependencies[self.tested_reference_str].options.get_safe("with_libglvnd") else "disabled"
        tc.project_options["osmesa"] = "enabled" if self.dependencies[self.tested_reference_str].options.get_safe("osmesa") else "disabled"
        tc.generate()

    def build(self):
        meson = Meson(self)
        meson.configure()
        meson.build()

    def test(self):
        if can_run(self):
            bin_path = os.path.join(self.cpp.build.bindir, "test_package")
            self.run(bin_path, env="conanrun")