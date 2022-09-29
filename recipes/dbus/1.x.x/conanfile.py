from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.apple import is_apple_os
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get, mkdir, rename, replace_in_file, rmdir, save
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout, cmake_layout
from conan.tools.meson import Meson, MesonToolchain
from conan.tools.scm import Version
import os
import textwrap

required_conan_version = ">=1.52.0"


class DbusConan(ConanFile):
    name = "dbus"
    license = ("AFL-2.1", "GPL-2.0-or-later")
    url = "https://github.com/conan-io/conan-center-index"
    homepage = "https://www.freedesktop.org/wiki/Software/dbus"
    description = "D-Bus is a simple system for interprocess communication and coordination."
    topics = ("bus", "interprocess", "message")
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "system_socket": ["ANY"],
        "system_pid_file": ["ANY"],
        "with_x11": [True, False],
        "with_glib": [True, False],
        "with_systemd": [True, False],
        "with_selinux": [True, False],
        "session_socket_dir": ["ANY"],
    }
    default_options = {
        "system_socket": "",
        "system_pid_file": "",
        "with_x11": False,
        "with_glib": False,
        "with_systemd": False,
        "with_selinux": False,
        "session_socket_dir": "/tmp",
    }

    @property
    def _meson_available(self):
        return Version(self.version) >= "1.15.0"

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os not in ("Linux", "FreeBSD") or Version(self.version) < "1.14.0":
            del self.options.with_systemd
        if self.settings.os not in ("Linux", "FreeBSD"):
            del self.options.with_x11

    def configure(self):
        try:
            del self.settings.compiler.libcxx
        except Exception:
            pass
        try:
            del self.settings.compiler.cppstd
        except Exception:
            pass

    def layout(self):
        if self._meson_available:
            basic_layout(self, src_folder="src")
        else:
            cmake_layout(self, src_folder="src")

    def build_requirements(self):
        if self._meson_available:
            self.tool_requires("meson/0.63.2")
            self.tool_requires("pkgconf/1.9.3")

    def requirements(self):
        self.requires("expat/2.4.9")
        if self.options.with_glib:
            self.requires("glib/2.74.0")
        if self.options.get_safe("with_systemd"):
            self.requires("libsystemd/251.4")
        if self.options.with_selinux:
            self.requires("libselinux/3.3")
        if self.options.get_safe("with_x11"):
            self.requires("xorg/system")

    def validate(self):
        if Version(self.version) >= "1.14.0":
            if self.info.settings.compiler == "gcc" and Version(self.info.settings.compiler.version) < 7:
                raise ConanInvalidConfiguration(f"{self.ref} requires at least gcc 7.")
            if self.info.settings.os == "Windows":
                raise ConanInvalidConfiguration(f"{self.ref} does not support windows. Contributions are welcome")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], destination=self.source_folder, strip_root=True)

    def generate(self):
        if self._meson_available:
            tc = MesonToolchain(self)
            tc.project_options["asserts"] = not is_apple_os(self)
            tc.project_options["checks"] = False
            tc.project_options["doxygen_docs"] = "disabled"
            tc.project_options["modular_tests"] = "disabled"
            tc.project_options["session_socket_dir"] = str(self.options.session_socket_dir)
            tc.project_options["selinux"] = "enabled" if self.options.get_safe("with_selinux", False) else "disabled"
            tc.project_options["systemd"] = "enabled" if self.options.get_safe("with_systemd", False) else "disabled"
            if self.options.get_safe("with_systemd", False):
                tc.project_options["systemd_system_unitdir"] = os.path.join(self.package_folder, "lib", "systemd", "system")
                tc.project_options["systemd_user_unitdir"] = os.path.join(self.package_folder, "lib", "systemd", "user")
            tc.project_options["x11_autolaunch"] = "enabled" if self.options.get_safe("with_x11", False) else "disabled"
            tc.project_options["xml_docs"] = "disabled"
            tc.generate()
            env = VirtualBuildEnv(self)
            env.generate(scope="build")
        else:
            tc = CMakeToolchain(self)
            tc.cache_variables["DBUS_BUILD_TESTS"] = False
            tc.cache_variables["DBUS_ENABLE_DOXYGEN_DOCS"] = False
            tc.cache_variables["DBUS_ENABLE_XML_DOCS"] = False
            tc.cache_variables["DBUS_BUILD_X11"] = bool(self.options.get_safe("with_x11", False))
            tc.cache_variables["ENABLE_SYSTEMD"] = "ON" if self.options.get_safe("with_systemd", False) else "OFF"
            tc.cache_variables["DBUS_WITH_GLIB"] = bool(self.options.get_safe("with_glib", False))
            tc.cache_variables["DBUS_DISABLE_ASSERT"] = is_apple_os(self)
            tc.cache_variables["DBUS_DISABLE_CHECKS"] = False

            # Conan does not provide an EXPAT_LIBRARIES CMake variable for the Expat library.
            # Define EXPAT_LIBRARIES to be the expat::expat target provided by Conan to fix linking.
            tc.cache_variables["EXPAT_LIBRARIES"] = "expat::expat"

            # https://github.com/freedesktop/dbus/commit/e827309976cab94c806fda20013915f1db2d4f5a
            tc.cache_variables["DBUS_SESSION_SOCKET_DIR"] = str(self.options.session_socket_dir)
            tc.generate()
            cmake_deps = CMakeDeps(self)
            cmake_deps.generate()
        pkg_config_deps = PkgConfigDeps(self)
        pkg_config_deps.generate()

    def _patch_sources(self):
        apply_conandata_patches(self)
        if not self._meson_available:
            # Unfortunately, there is currently no other way to force disable
            # CMAKE_FIND_PACKAGE_PREFER_CONFIG ON in CMake conan_toolchain.
            replace_in_file(
                self,
                os.path.join(self.generators_folder, "conan_toolchain.cmake"),
                "set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)",
                "",
                strict=False,
            )

    def build(self):
        self._patch_sources()
        if self._meson_available:
            meson = Meson(self)
            meson.configure()
            meson.build()
        else:
            cmake = CMake(self)
            build_script_folder = None
            if Version(self.version) < "1.14.0":
                build_script_folder = "cmake"
            cmake.configure(build_script_folder=build_script_folder)
            cmake.build()

    def package(self):
        copy(self, "COPYING", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        if self._meson_available:
            meson = Meson(self)
            meson.install()
        else:
            cmake = CMake(self)
            cmake.install()

        rmdir(self, os.path.join(self.package_folder, "share", "doc"))
        mkdir(self, os.path.join(self.package_folder, "res"))
        for i in ["var", "share", "etc"]:
            rename(self, os.path.join(self.package_folder, i), os.path.join(self.package_folder, "res", i))

        rmdir(self, os.path.join(self.package_folder, "lib", "cmake"))
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))
        rmdir(self, os.path.join(self.package_folder, "lib", "systemd"))

        # TODO: to remove in conan v2 once cmake_find_package_* generators removed
        self._create_cmake_module_alias_targets(
            os.path.join(self.package_folder, self._module_file_rel_path),
            {"dbus-1": "dbus-1::dbus-1"}
        )

    def _create_cmake_module_alias_targets(self, module_file, targets):
        content = ""
        for alias, aliased in targets.items():
            content += textwrap.dedent(f"""\
                if(TARGET {aliased} AND NOT TARGET {alias})
                    add_library({alias} INTERFACE IMPORTED)
                    set_property(TARGET {alias} PROPERTY INTERFACE_LINK_LIBRARIES {aliased})
                endif()
            """)
        save(self, module_file, content)

    @property
    def _module_file_rel_path(self):
        return os.path.join("lib", "cmake", f"conan-official-{self.name}-targets.cmake")

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "DBus1")
        self.cpp_info.set_property("cmake_target_name", "dbus-1")
        self.cpp_info.set_property("pkg_config_name", "dbus-1")
        self.cpp_info.includedirs.extend([
            os.path.join("include", "dbus-1.0"),
            os.path.join("lib", "dbus-1.0", "include"),
        ])
        self.cpp_info.resdirs = ["res"]
        self.cpp_info.libs = ["dbus-1"]
        if self.settings.os == "Linux":
            self.cpp_info.system_libs.append("rt")
        if self.settings.os == "Windows":
            self.cpp_info.system_libs.extend(["iphlpapi", "ws2_32"])
        else:
            self.cpp_info.system_libs.append("pthread")

        # TODO: to remove in conan v2 once cmake_find_package_* & pkg_config generators removed
        self.cpp_info.filenames["cmake_find_package"] = "DBus1"
        self.cpp_info.filenames["cmake_find_package_multi"] = "DBus1"
        self.cpp_info.names["cmake_find_package"] = "dbus-1"
        self.cpp_info.names["cmake_find_package_multi"] = "dbus-1"
        self.cpp_info.build_modules["cmake_find_package"] = [self._module_file_rel_path]
        self.cpp_info.build_modules["cmake_find_package_multi"] = [self._module_file_rel_path]
        self.cpp_info.names["pkg_config"] = "dbus-1"
