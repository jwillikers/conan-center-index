import os

from conan import ConanFile
from conan.tools.build.cross_building import cross_building
from conan.tools.meson import Meson, MesonToolchain
from conan.tools.layout import basic_layout
from conans import tools
from conans.errors import ConanInvalidConfiguration

required_conan_version = ">=1.43.0"

class WaylandScannerConan(ConanFile):
    name = "wayland-scanner"
    description = "Wayland is a project to define a protocol for a compositor to talk to its clients as well as a library implementation of the protocol"
    topics = ("protocol", "compositor", "display", "wayland")
    url = "https://github.com/conan-io/conan-center-index"
    homepage = "https://wayland.freedesktop.org"
    license = "MIT"

    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "enable_dtd_validation": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "enable_dtd_validation": True,
    }

    generators = "pkg_config", "PkgConfigDeps", "VirtualBuildEnv", "VirtualRunEnv"
    
    def validate(self):
        if self.settings.os != "Linux":
            raise ConanInvalidConfiguration("Wayland can be built on Linux only")

    def configure(self):
        del self.settings.compiler.libcxx
        del self.settings.compiler.cppstd
        if self.options.shared:
            del self.options.fPIC

    def requirements(self):
        self.requires("expat/2.4.8")

    def build_requirements(self):
        self.tool_requires("meson/0.62.2")
        self.tool_requires("pkgconf/1.7.4")
        if cross_building(self):
            self.tool_requires("wayland-scanner/%s" % self.version)

    def layout(self):
        basic_layout(self)

    def source(self):
        tools.get(**self.conan_data["sources"][self.version],
                  strip_root=True)

    def _patch_sources(self):
        tools.replace_in_file(os.path.join(self.source_folder, "meson.build"),
                              "subdir('tests')", "#subdir('tests')")

    def generate(self):
        tc = MesonToolchain(self)
        tc.project_options["libdir"] = "lib"
        tc.project_options["datadir"] = "res"
        tc.project_options["libraries"] = False
        tc.project_options["dtd_validation"] = self.options.enable_dtd_validation
        tc.project_options["documentation"] = False
        if tools.Version(self.version) >= "1.18.91":
            tc.project_options["scanner"] = True
        tc.generate()

    def build(self):
        self._patch_sources()
        meson = Meson(self)
        meson.configure()
        with tools.run_environment(self):
            meson.build()

    def package(self):
        self.copy(pattern="COPYING", dst="licenses", src=self.source_folder)
        meson = Meson(self)
        meson.install()
        tools.rmdir(os.path.join(self.package_folder, "lib", "pkgconfig"))

    def package_info(self):
        self.cpp_info.components["wayland-scanner"].set_property("pkg_config_name", "wayland-scanner")
        self.cpp_info.components["wayland-scanner"].names["pkg_config"] = "wayland-scanner"
        self.cpp_info.components["wayland-scanner"].resdirs = ["res"]
        self.cpp_info.components["wayland-scanner"].requires = ["expat::expat"]
        if self.options.enable_dtd_validation:
            self.cpp_info.components["wayland-scanner"].requires.append("libxml2::libxml2")
        pkgconfig_variables = {
            'datarootdir': '${prefix}/res',
            'pkgdatadir': '${datarootdir}/wayland',
            'bindir': '${prefix}/bin',
            'wayland_scanner': '${bindir}/wayland-scanner',
        }
        self.cpp_info.components["wayland-scanner"].set_property(
            "pkg_config_custom_content",
            "\n".join("%s=%s" % (key, value) for key,value in pkgconfig_variables.items()))

        bindir = os.path.join(self.package_folder, "bin")
        self.output.info("Appending PATH environment variable: {}".format(bindir))
        self.env_info.PATH.append(bindir)
