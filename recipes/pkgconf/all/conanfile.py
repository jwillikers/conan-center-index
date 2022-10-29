from conan import ConanFile
from conan.tools.apple import fix_apple_shared_install_name
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get, rename, replace_in_file, rm, rmdir
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain
from conan.tools.microsoft import is_msvc, unix_path
from conan.tools.scm import Version
import os

required_conan_version = ">= 1.52.0"


class PkgConfConan(ConanFile):
    name = "pkgconf"
    url = "https://github.com/conan-io/conan-center-index"
    homepage = "https://git.sr.ht/~kaniini/pkgconf"
    topics = "pkg-config"
    license = "ISC"
    description = "package compiler and linker metadata toolkit"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "enable_lib": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "enable_lib": False,
    }

    @property
    def _is_clang_cl(self):
        return self.settings.compiler == "clang" and self.settings.os == "Windows"

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if not self.options.enable_lib:
            try:
                del self.options.fPIC
            except Exception:
                pass
            del self.options.shared
        elif self.options.shared:
            try:
                del self.options.fPIC
            except Exception:
                pass
        try:
            del self.settings.compiler.libcxx
        except Exception:
            pass
        try:
            del self.settings.compiler.cppstd
        except Exception:
            pass

    def build_requirements(self):
        self.tool_requires("meson/0.63.3")

    def layout(self):
        basic_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"][self.version],
            destination=self.source_folder, strip_root=True)

    @property
    def _sharedstatedir(self):
        return os.path.join(self.package_folder, "bin", "share")

    def generate(self):
        virtual_build_env = VirtualBuildEnv(self)
        virtual_build_env.generate()
        tc = MesonToolchain(self)
        tc.project_options["tests"] = False
        tc.project_options["sharedstatedir"] = self._sharedstatedir
        if not self.options.enable_lib:
            tc.project_options["default_library"] = "static"
        tc.generate()

    def _patch_sources(self):
        apply_conandata_patches(self)
        if not self.options.get_safe("shared", False):
            replace_in_file(self, os.path.join(self.source_folder, "meson.build"),
                                  "'-DLIBPKGCONF_EXPORT'",
                                  "'-DPKGCONFIG_IS_STATIC'")
        replace_in_file(self, os.path.join(self.source_folder, "meson.build"),
            "project('pkgconf', 'c',",
            "project('pkgconf', 'c',\ndefault_options : ['c_std=gnu99'],")

    def build(self):
        self._patch_sources()
        meson = Meson(self)
        meson.configure()
        meson.build()

    def package(self):
        copy(self, "COPYING", self.source_folder, os.path.join(self.package_folder, "licenses"))
        meson = Meson(self)
        meson.install()

        if is_msvc(self):
            rm(self, "*.pdb", os.path.join(self.package_folder, "bin"))
            if self.options.enable_lib and not self.options.shared:
                rename(self, os.path.join(self.package_folder, "lib", "libpkgconf.a"),
                        os.path.join(self.package_folder, "lib", "pkgconf.lib"))

        if self.options.enable_lib:
            fix_apple_shared_install_name(self)
        else:
            rmdir(self, os.path.join(self.package_folder, "lib"))
            rmdir(self, os.path.join(self.package_folder, "include"))

        rmdir(self, os.path.join(self.package_folder, "share", "man"))
        rename(self, os.path.join(self.package_folder, "share", "aclocal"),
                os.path.join(self.package_folder, "bin", "aclocal"))
        rmdir(self, os.path.join(self.package_folder, "share"))
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))

    def package_id(self):
        if not self.options.enable_lib:
            del self.info.settings.compiler

    def package_info(self):
        if self.options.enable_lib:
            self.cpp_info.set_property("pkg_config_name", "libpkgconf")
            if Version(self.version) >= "1.7.4":
                self.cpp_info.includedirs.append(os.path.join("include", "pkgconf"))
            self.cpp_info.libs = ["pkgconf"]
            if not self.options.shared:
                self.cpp_info.defines = ["PKGCONFIG_IS_STATIC"]
        else:
            self.cpp_info.includedirs = []
            self.cpp_info.libdirs = []

        bindir = os.path.join(self.package_folder, "bin")
        self.output.info(f"Appending PATH env var: {bindir}")
        self.env_info.PATH.append(bindir)

        exesuffix = ".exe" if self.settings.os == "Windows" else ""
        pkg_config = os.path.join(bindir, "pkgconf" + exesuffix).replace("\\", "/")
        self.conf_info.define("tools.gnu:pkg_config", pkg_config)
        self.output.info(f"Setting PKG_CONFIG env var: {pkg_config}")
        self.buildenv_info.define_path("PKG_CONFIG", pkg_config)
        self.env_info.PKG_CONFIG = pkg_config # remove in conan v2?

        automake_extra_includes = unix_path(self, os.path.join(self.package_folder , "bin", "aclocal").replace("\\", "/"))
        self.output.info(f"Appending AUTOMAKE_CONAN_INCLUDES env var: {automake_extra_includes}")
        self.buildenv_info.prepend_path("AUTOMAKE_CONAN_INCLUDES", automake_extra_includes)
        self.env_info.AUTOMAKE_CONAN_INCLUDES.append(automake_extra_includes) # remove in conan v2?

        # TODO: to remove in conan v2 once pkg_config generator removed
        if self.options.enable_lib:
            self.cpp_info.names["pkg_config"] = "libpkgconf"
