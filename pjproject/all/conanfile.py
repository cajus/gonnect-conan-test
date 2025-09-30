import os
import shutil
from conan import ConanFile
from conan.tools.files import get, replace_in_file, rmdir, copy, apply_conandata_patches, export_conandata_patches, collect_libs
from conan.tools.build import cross_building
from conan.tools.layout import basic_layout
from conan.tools.microsoft import is_msvc
from conan.tools.apple import fix_apple_shared_install_name
from conan.tools.env import VirtualRunEnv
from conan.tools.gnu import AutotoolsToolchain, AutotoolsDeps, Autotools
from conan.errors import ConanInvalidConfiguration

required_conan_version = ">=2"


class PjSIPConan(ConanFile):
    name = "pjproject"
    description = "A set of functions for use by applications that allow users to edit command lines as they are typed in"
    topics = ("sip", "communication")
    license = "GPL-2.0"
    homepage = "http://www.pjsip.org"
    url = "https://github.com/pjsip/pjproject"

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "with_uuid": [True, False],
        "with_samplerate": [True, False],
        "with_ext_sound": [True, False],
        "with_video": [True, False],
        "with_floatingpoint": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "with_uuid": True,
        "with_samplerate": False,
        "with_ext_sound": True,
        "with_video": False,
        "with_floatingpoint": True,
    }

    implements = ["auto_shared_fpic"]
    languages = "C"

    def requirements(self):
        self.requires("openssl/[>=3 <4]")

        if self.options.with_uuid:
            self.requires("libuuid/1.0.3")
        if self.options.with_samplerate:
            self.requires("libsamplerate/0.2.2")

    def layout(self):
        basic_layout(self, src_folder="src")

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        if not cross_building(self):
            # Expose LD_LIBRARY_PATH when there are shared dependencies,
            # as configure tries to run a test executable (when not cross-building)
            env = VirtualRunEnv(self)
            env.generate(scope="build")

        tc = AutotoolsToolchain(self)
        if not self.options.with_uuid:
            tc.configure_args.append("--disable-uuid")
        if self.options.with_samplerate:
            tc.configure_args.append("--enable-libsamplerate")
        if not self.options.with_video:
            tc.configure_args.append("--disable-video")
        if not self.options.with_floatingpoint:
            tc.configure_args.append("--disable-floating-point")
        if self.options.with_ext_sound:
            tc.configure_args.append("--enable-ext-sound")

        if cross_building(self):
            tc.configure_args.append("bash_cv_wcwidth_broken=yes")

        tc.configure_args.append("--disable-install-examples")
        tc.extra_cflags.append("-DPJ_HAS_IPV6=1")
        tc.generate()

        deps = AutotoolsDeps(self)
        deps.generate()

    def build(self):
        apply_conandata_patches(self)
        shutil.copytree(self.source_folder, self.build_folder, dirs_exist_ok=True)

        autotools = Autotools(self)
        autotools.configure()
        autotools.make()

    def package(self):
        copy(self, "COPYING", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        autotools = Autotools(self)
        autotools.install()

        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))
        rmdir(self, os.path.join(self.package_folder, "share"))
        fix_apple_shared_install_name(self)

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "pjproject")
        self.cpp_info.set_property("pkg_config_name", "libpjproject")
        self.cpp_info.libs = collect_libs(self)
