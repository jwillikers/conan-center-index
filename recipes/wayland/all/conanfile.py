import os

from conan import ConanFile
from conan.tools.build.cross_building import cross_building
from conan.tools.meson import Meson, MesonToolchain
from conan.tools.layout import basic_layout
from conans import tools
from conans.errors import ConanInvalidConfiguration

required_conan_version = ">=1.43.0"

class WaylandConan(ConanFile):
    name = "wayland"
    description = "Wayland is a project to define a protocol for a compositor to talk to its clients as well as a library implementation of the protocol"
    topics = ("protocol", "compositor", "display")
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
        if self.options.enable_dtd_validation:
            self.requires("libxml2/2.9.14")
        self.requires("expat/2.4.8")
        self.requires("libffi/3.4.2")

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
        tc.project_options["libraries"] = True
        tc.project_options["dtd_validation"] = self.options.enable_dtd_validation
        tc.project_options["documentation"] = False
        if tools.Version(self.version) >= "1.18.91":
            tc.project_options["scanner"] = False
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
        self.cpp_info.components["wayland-server"].libs = ["wayland-server"]
        self.cpp_info.components["wayland-server"].set_property("pkg_config_name", "wayland-server")
        self.cpp_info.components["wayland-server"].names["pkg_config"] = "wayland-server"
        self.cpp_info.components["wayland-server"].requires = ["libffi::libffi"]
        self.cpp_info.components["wayland-server"].system_libs = ["pthread", "m"]
        self.cpp_info.components["wayland-server"].resdirs = ["res"]
        pkgconfig_variables = {
            'datarootdir': '${prefix}/res',
            'pkgdatadir': '${datarootdir}/wayland',
        }
        self.cpp_info.components["wayland-server"].set_property(
            "pkg_config_custom_content",
            "\n".join("%s=%s" % (key, value) for key,value in pkgconfig_variables.items()))

        self.cpp_info.components["wayland-client"].libs = ["wayland-client"]
        self.cpp_info.components["wayland-client"].set_property("pkg_config_name", "wayland-client")
        self.cpp_info.components["wayland-client"].names["pkg_config"] = "wayland-client"
        self.cpp_info.components["wayland-client"].requires = ["libffi::libffi"]
        self.cpp_info.components["wayland-client"].system_libs = ["pthread", "m"]
        self.cpp_info.components["wayland-client"].resdirs = ["res"]
        pkgconfig_variables = {
            'datarootdir': '${prefix}/res',
            'pkgdatadir': '${datarootdir}/wayland',
        }
        self.cpp_info.components["wayland-client"].set_property(
            "pkg_config_custom_content",
            "\n".join("%s=%s" % (key, value) for key,value in pkgconfig_variables.items()))

        self.cpp_info.components["wayland-cursor"].libs = ["wayland-cursor"]
        self.cpp_info.components["wayland-cursor"].set_property("pkg_config_name", "wayland-cursor")
        self.cpp_info.components["wayland-cursor"].names["pkg_config"] = "wayland-cursor"
        self.cpp_info.components["wayland-cursor"].requires = ["wayland-client"]

        self.cpp_info.components["wayland-egl"].libs = ["wayland-egl"]
        self.cpp_info.components["wayland-egl"].set_property("pkg_config_name", "wayland-egl")
        self.cpp_info.components["wayland-egl"].names["pkg_config"] = "wayland-egl"
        self.cpp_info.components["wayland-egl"].requires = ["wayland-client"]

        self.cpp_info.components["wayland-egl-backend"].names["pkg_config"] = "wayland-egl-backend"
        self.cpp_info.components["wayland-egl-backend"].set_property("pkg_config_name", "wayland-egl-backend")
        self.cpp_info.components["wayland-egl-backend"].version = "3"
