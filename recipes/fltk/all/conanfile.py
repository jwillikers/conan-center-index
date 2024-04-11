import os
import textwrap

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.apple import is_apple_os
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, collect_libs, copy, export_conandata_patches, get, rm, rmdir, save
from conan.tools.gnu import PkgConfigDeps
from conan.tools.scm import Version

required_conan_version = ">=1.53.0"


class FltkConan(ConanFile):
    name = "fltk"
    description = "Fast Light Toolkit is a cross-platform C++ GUI toolkit"
    license = "LGPL-2.1-or-later WITH FLTK-exception"
    url = "https://github.com/conan-io/conan-center-index"
    homepage = "https://www.fltk.org"
    topics = ("gui",)

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "with_cairo": [True, False],
        "with_pango": [True, False],
        "with_gl": [True, False],
        "with_threads": [True, False],
        "with_gdiplus": [True, False],
        "abi_version": [None, "ANY"],
        "with_wayland": [True, False],
        "with_x11": [True, False],
        "with_xft": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "with_cairo": True,
        "with_pango": True,
        "with_gl": True,
        "with_threads": True,
        "with_gdiplus": True,
        "abi_version": None,
        "with_wayland": True,
        "with_x11": True,
        "with_xft": False,
    }

    @property
    def _has_build_profile(self):
        return hasattr(self, "settings_build")

    @property
    def _has_with_cairo_option(self):
        return Version(self.version) >= "1.4.0"

    @property
    def _has_with_pango_option(self):
        return Version(self.version) >= "1.4.0"

    @property
    def _has_with_wayland_option(self):
        return Version(self.version) >= "1.4.0" and self.settings.os == "Linux"

    @property
    def _has_with_x11_option(self):
        return Version(self.version) >= "1.4.0" and self.settings.os in ["FreeBSD", "Linux"]

    @property
    def _with_x11(self):
        return self.settings.os in ["FreeBSD", "Linux"] and Version(self.version) < "1.4.0" or self.options.get_safe("with_x11")

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC
        else:
            self.options.rm_safe("with_gdiplus")

        if self.options.abi_version is None:
            _version_token = self.version.split(".")
            _version_major = int(_version_token[0])
            if len(_version_token) >= 3:
                _version_minor = int(_version_token[1])
                _version_patch = int(_version_token[2])
            elif len(_version_token) >= 2:
                _version_minor = int(_version_token[1])
                _version_patch = 0
            self.options.abi_version = str(
                int(_version_major) * 10000 + int(_version_minor) * 100 + int(_version_patch)
            )
        if not self._has_with_cairo_option:
            self.options.rm_safe("with_cairo")
        if not self._has_with_pango_option:
            self.options.rm_safe("with_pango")
        if not self._has_with_wayland_option:
            self.options.rm_safe("with_wayland")
        if not self._has_with_x11_option:
            self.options.rm_safe("with_x11")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        cmake_layout(self, src_folder="src")

    def requirements(self):
        self.requires("zlib/[>=1.2.11 <2]")
        self.requires("libjpeg/9e")
        self.requires("libpng/[>=1.6 <2]")
        if self.options.get_safe("with_cairo"):
            self.requires("cairo/1.18.0")
        if self.options.get_safe("with_pango"):
            self.requires("pango/1.51.0")
            # todo Enforce requirement on pangocairo.
        if self._with_x11:
            self.requires("xorg/system")
        if self.options.get_safe("with_wayland"):
            self.requires("wayland/1.22.0")
            self.requires("xkbcommon/1.6.0")
        if self.settings.os in ["FreeBSD", "Linux"]:
            if self.options.with_gl:
                self.requires("opengl/system")
                if is_apple_os(self) or self.settings.os == "Windows":
                    self.requires("glu/system")
                else:
                    self.requires("mesa-glu/9.0.3")
            self.requires("fontconfig/2.15.0")
            if self.options.with_xft:
                self.requires("libxft/2.3.8")

    def validate(self):
        if self.options.get_safe("with_pango") and not self.dependencies["pango"].options.with_cairo:
            raise ConanInvalidConfiguration(f"{self.ref} requires the with_cairo option of pango to be enabled when the with_pango option is enabled")

    def build_requirements(self):
        if not self.conf.get("tools.gnu:pkg_config", default=False, check_type=str):
            self.tool_requires("pkgconf/2.1.0")
        if self.options.get_safe("with_wayland"):
            if self._has_build_profile:
                self.tool_requires("wayland/<host_version>")
            self.tool_requires("wayland-protocols/1.33")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["FLTK_BUILD_TEST"] = False
        tc.variables["FLTK_BUILD_EXAMPLES"] = False
        if Version(self.version) < "1.4.0":
            tc.variables["OPTION_BUILD_SHARED_LIBS"] = self.options.shared
            tc.variables["OPTION_USE_GL"] = self.options.with_gl
            tc.variables["OPTION_USE_THREADS"] = self.options.with_threads
            tc.variables["OPTION_BUILD_HTML_DOCUMENTATION"] = False
            tc.variables["OPTION_BUILD_PDF_DOCUMENTATION"] = False
            tc.variables["OPTION_USE_XFT"] = self.options.with_xft
            if self.options.abi_version:
                tc.variables["OPTION_ABI_VERSION"] = self.options.abi_version
            tc.variables["OPTION_USE_SYSTEM_LIBJPEG"] = True
            tc.variables["OPTION_USE_SYSTEM_ZLIB"] = True
            tc.variables["OPTION_USE_SYSTEM_LIBPNG"] = True
        else:
            tc.variables["FLTK_BUILD_SHARED_LIBS"] = self.options.shared
            tc.variables["FLTK_BUILD_GL"] = self.options.with_gl
            tc.variables["FLTK_USE_PTHREADS"] = self.options.with_threads
            tc.variables["FLTK_BUILD_HTML_DOCS"] = False
            tc.variables["FLTK_BUILD_PDF_DOCS"] = False
            tc.variables["FLTK_USE_XFT"] = self.options.with_xft
            if self.options.abi_version:
                tc.variables["FLTK_ABI_VERSION"] = self.options.abi_version
            tc.variables["FLTK_USE_SYSTEM_LIBJPEG"] = True
            tc.variables["FLTK_USE_SYSTEM_ZLIB"] = True
            tc.variables["FLTK_USE_SYSTEM_LIBPNG"] = True
            tc.variables["FLTK_USE_CAIRO"] = self.options.get_safe("with_cairo")
            tc.variables["FLTK_USE_PANGO"] = self.options.get_safe("with_pango")
            tc.variables["FLTK_BACKEND_WAYLAND"] = self.options.get_safe("with_wayland")
            tc.variables["FLTK_BACKEND_X11"] = self.options.get_safe("with_x11")
        tc.generate()
        pkg_config_deps = PkgConfigDeps(self)
        if self.options.get_safe("with_wayland"):
            if self._has_build_profile:
                pkg_config_deps.build_context_activated = ["wayland", "wayland-protocols"]
                pkg_config_deps.build_context_suffix = {"wayland": "_BUILD"}
            else:
                # Manually generate pkgconfig file of wayland-protocols since
                # PkgConfigDeps.build_context_activated can't work with legacy 1 profile
                # We must use legacy conan v1 deps_cpp_info because self.dependencies doesn't
                # contain build requirements when using 1 profile.
                wp_prefix = self.deps_cpp_info["wayland-protocols"].rootpath
                wp_version = self.deps_cpp_info["wayland-protocols"].version
                wp_pkg_content = textwrap.dedent(f"""\
                    prefix={wp_prefix}
                    datarootdir=${{prefix}}/res
                    pkgdatadir=${{datarootdir}}/wayland-protocols
                    Name: Wayland Protocols
                    Description: Wayland protocol files
                    Version: {wp_version}
                """)
                save(self, os.path.join(self.generators_folder, "wayland-protocols.pc"), wp_pkg_content)
        pkg_config_deps.generate()
        tc = CMakeDeps(self)
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, "COPYING", self.source_folder, os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()
        rmdir(self, os.path.join(self.package_folder, "share"))
        rmdir(self, os.path.join(self.package_folder, "FLTK.framework"))
        rmdir(self, os.path.join(self.package_folder, "CMake"))
        rm(self, "fltk-config*", os.path.join(self.package_folder, "bin"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "fltk")
        self.cpp_info.set_property("cmake_target_name", "fltk::fltk")
        self.cpp_info.libs = collect_libs(self)

        if self.settings.os in ("Linux", "FreeBSD"):
            if self.options.with_threads:
                self.cpp_info.system_libs.extend(["pthread", "dl"])
            if self.options.with_gl:
                self.cpp_info.system_libs.append("GL")
        elif is_apple_os(self):
            self.cpp_info.frameworks = [
                "AppKit", "ApplicationServices", "Carbon", "Cocoa", "CoreFoundation", "CoreGraphics",
                "CoreText", "CoreVideo", "Foundation", "IOKit",
            ]
            if self.options.with_gl:
                self.cpp_info.frameworks.append("OpenGL")
        elif self.settings.os == "Windows":
            if self.options.shared:
                self.cpp_info.defines.append("FL_DLL")
            self.cpp_info.system_libs = ["gdi32", "imm32", "msimg32", "ole32", "oleaut32", "uuid", "comctl32"]
            if self.options.get_safe("with_gdiplus"):
                self.cpp_info.system_libs.append("gdiplus")
            if self.options.with_gl:
                self.cpp_info.system_libs.append("opengl32")

        # TODO: to remove in conan v2 once legacy generators removed
        self.cpp_info.names["cmake_find_package"] = "fltk"
        self.cpp_info.names["cmake_find_package_multi"] = "fltk"
