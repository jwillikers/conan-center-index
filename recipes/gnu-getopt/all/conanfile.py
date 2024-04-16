import os

from conan import ConanFile
from conan.tools.env import VirtualBuildEnv, VirtualRunEnv
from conan.tools.files import copy, get
from conan.tools.meson import Meson, MesonToolchain
from conan.tools.layout import basic_layout

required_conan_version = ">=1.54.0"


class GnuGetoptConan(ConanFile):
    name = "gnu-getopt"
    description = "GNU getopt(1) command-line utility"
    license = "GPL-2.0-or-later"
    url = "https://github.com/conan-io/conan-center-index"
    homepage = "http://frodo.looijaard.name/project/getopt"
    topics = ("gnu", "getopt", "utility", "command-line", "parsing")
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    @property
    def _settings_build(self):
        return getattr(self, "settings_build", self.settings)

    def layout(self):
        basic_layout(self, src_folder="src")

    def package_id(self):
        del self.info.settings.compiler

    def build_requirements(self):
        self.tool_requires("meson/1.4.0")
        if self._settings_build.os == "Windows":
            self.win_bash = True
            if not self.conf.get("tools.microsoft.bash:path", check_type=str):
                self.tool_requires("msys2/cci.latest")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = MesonToolchain(self)
        tc.project_options["auto_features"] = "disabled"
        # Enable libutil for older versions of glibc which still provide an actual libutil library.
        tc.project_options["libutil"] = "enabled"
        tc.project_options["program-tests"] = False
        if "x86" in self.settings.arch:
            tc.c_args.append("-mstackrealign")
        tc.generate()
        build_env = VirtualBuildEnv(self)
        build_env.generate()
        run_env = VirtualRunEnv(self)
        run_env.generate()

    def build(self):
        meson = Meson(self)
        meson.configure()
        meson.build()

    def package(self):
        copy(self, "COPYING", self.source_folder, os.path.join(self.package_folder, "licenses"))
        copy(self, "getopt*", self.build_folder, os.path.join(self.package_folder, "bin"))

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.frameworkdirs = []
