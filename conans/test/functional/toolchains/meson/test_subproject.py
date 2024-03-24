import os
import textwrap

import pytest

from conans.test.assets.sources import gen_function_c
from conans.test.functional.toolchains.meson._base import TestMesonBase


class MesonSubprojectTest(TestMesonBase):
    _conanfile_py = textwrap.dedent("""
        import os
        import shutil
        from conan import ConanFile
        from conan.tools.meson import Meson, MesonToolchain


        class App(ConanFile):
            settings = "os", "arch", "compiler", "build_type"
            options = {"shared": [True, False], "fPIC": [True, False]}
            default_options = {"shared": False, "fPIC": True}
            exports_sources = "**"

            def config_options(self):
                if self.settings.os == "Windows":
                    self.options.rm_safe("fPIC")

            def configure(self):
                if self.options.shared:
                    self.options.rm_safe("fPIC")

            def layout(self):
                self.folders.build = "build"

            def generate(self):
                tc = MesonToolchain(self)
                tc.generate()

            def build(self):
                meson = Meson(self)
                meson.configure()
                meson.build()

            def package(self):
                meson = Meson(self)
                meson.install()

                # https://mesonbuild.com/FAQ.html#why-does-building-my-project-with-msvc-output-static-libraries-called-libfooa
                #if self.settings.compiler == 'msvc' and not self.options.shared:
                #    shutil.move(os.path.join(self.package_folder, "lib", "libhello.a"),
                #                os.path.join(self.package_folder, "lib", "hello.lib"))

            def package_info(self):
                self.cpp_info.components["hello"].libs = ['hello']
                self.cpp_info.components["greeter"].libs = ['greeter']
                self.cpp_info.components["greeter"].requires = ['hello']
        """)
    _conanfil_with_option_py = textwrap.dedent("""
        import os
        import shutil
        from conan import ConanFile
        from conan.tools.meson import Meson, MesonToolchain


        class App(ConanFile):
            settings = "os", "arch", "compiler", "build_type"
            options = {"shared": [True, False], "fPIC": [True, False]}
            default_options = {"shared": False, "fPIC": True}
            exports_sources = "**"

            def config_options(self):
                if self.settings.os == "Windows":
                    self.options.rm_safe("fPIC")

            def configure(self):
                if self.options.shared:
                    self.options.rm_safe("fPIC")

            def layout(self):
                self.folders.build = "build"

            def generate(self):
                tc = MesonToolchain(self)
                tc.subproject_options["hello"] = [{'french': 'true'}]
                tc.generate()

            def build(self):
                meson = Meson(self)
                meson.configure()
                meson.build()

            def package(self):
                meson = Meson(self)
                meson.install()

                # https://mesonbuild.com/FAQ.html#why-does-building-my-project-with-msvc-output-static-libraries-called-libfooa
                #if self.settings.compiler == 'msvc' and not self.options.shared:
                #    shutil.move(os.path.join(self.package_folder, "lib", "libhello.a"),
                #                os.path.join(self.package_folder, "lib", "hello.lib"))

            def package_info(self):
                self.cpp_info.components["hello"].libs = ['hello']
                self.cpp_info.components["greeter"].libs = ['greeter']
                self.cpp_info.components["greeter"].requires = ['hello']
        """)

    _meson_build = textwrap.dedent("""
        project('greeter', 'c')

        hello_proj = subproject('hello')
        hello_dep = hello_proj.get_variable('hello_dep')

        inc = include_directories('include')
        greeter = static_library('greeter',
            'greeter.c',
            include_directories : inc,
            dependencies : hello_dep,
            install : true)

        install_headers('greeter.h')
        """)

    _meson_subproject_build = textwrap.dedent("""
        project('hello', 'c')

        hello_c_args = []
            if get_option('french')
            hello_c_args = ['-DFRENCH']
        endif

        inc = include_directories('include')
        hello = static_library('hello',
            'hello.c',
            include_directories : inc,
            c_args: hello_c_args,
            install : true)

        hello_dep = declare_dependency(include_directories : inc,
            link_with : hello)
        """)

    _meson_subproject_options = textwrap.dedent("""
        option('french', type : 'boolean', value : false)
        """)

    _hello_c = textwrap.dedent("""
        #include <stdio.h>

        void hello(void) {
        #ifdef FRENCH
            printf("Le sous-projet vous salut\\n");
        #else
            printf("Hello from subproject\\n");
        #endif
        }
        """)

    _greeter_c = textwrap.dedent("""
        #include <hello.h>

        void greeter(void) {
            hello();
        }
        """)

    _hello_h = textwrap.dedent("""
        #pragma once
        void hello(void);
        """)

    _greeter_h = textwrap.dedent("""
        #pragma once
        void greeter(void);
        """)

    _test_package_conanfile_py = textwrap.dedent("""
        import os
        from conan import ConanFile
        from conan.tools.cmake import CMake, cmake_layout
        from conan.tools.build import cross_building

        class TestConan(ConanFile):
            settings = "os", "compiler", "build_type", "arch"
            generators = "CMakeToolchain", "CMakeDeps"

            def requirements(self):
                self.requires(self.tested_reference_str)

            def layout(self):
                cmake_layout(self)

            def build(self):
                cmake = CMake(self)
                cmake.configure()
                cmake.build()

            def test(self):
                if not cross_building(self):
                    cmd = os.path.join(self.cpp.build.bindirs[0], "test_package")
                    self.run(cmd, env=["conanrunenv"])
        """)

    _test_package_cmake_lists = textwrap.dedent("""
        cmake_minimum_required(VERSION 3.1)
        project(test_package C)

        add_executable(${PROJECT_NAME} src/test_package.c)
        find_package(greeter CONFIG REQUIRED)
        target_link_libraries(${PROJECT_NAME} greeter::greeter)
        """)

    @pytest.mark.tool("meson")
    def test_subproject(self):
        test_package_c = gen_function_c(name="main", includes=["greeter"], calls=["greeter"])

        self.t.save({"conanfile.py": self._conanfile_py,
                     "meson.build": self._meson_build,
                     "greeter.c": self._greeter_c,
                     "greeter.h": self._greeter_h,
                     os.path.join("include", "greeter.h"): self._greeter_h,
                     os.path.join("subprojects", "hello", "include", "hello.h"): self._hello_h,
                     os.path.join("subprojects", "hello", "hello.c"): self._hello_c,
                     os.path.join("subprojects", "hello", "meson.build"): self._meson_subproject_build,
                     os.path.join("subprojects", "hello", "meson.options"): self._meson_subproject_options,
                     os.path.join("test_package", "conanfile.py"): self._test_package_conanfile_py,
                     os.path.join("test_package", "CMakeLists.txt"): self._test_package_cmake_lists,
                     os.path.join("test_package", "src", "test_package.c"): test_package_c})

        self.t.run("create . greeter/0.1@")
        assert "Hello from subproject" in self.t.out


    @pytest.mark.tool("meson")
    def test_subproject_with_options(self):
        test_package_c = gen_function_c(name="main", includes=["greeter"], calls=["greeter"])

        self.t.save({"conanfile.py": self._conanfil_with_option_py,
                     "meson.build": self._meson_build,
                     "greeter.c": self._greeter_c,
                     "greeter.h": self._greeter_h,
                     os.path.join("include", "greeter.h"): self._greeter_h,
                     os.path.join("subprojects", "hello", "include", "hello.h"): self._hello_h,
                     os.path.join("subprojects", "hello", "hello.c"): self._hello_c,
                     os.path.join("subprojects", "hello", "meson.build"): self._meson_subproject_build,
                     os.path.join("subprojects", "hello", "meson.options"): self._meson_subproject_options,
                     os.path.join("test_package", "conanfile.py"): self._test_package_conanfile_py,
                     os.path.join("test_package", "CMakeLists.txt"): self._test_package_cmake_lists,
                     os.path.join("test_package", "src", "test_package.c"): test_package_c})

        self.t.run("create . greeter/0.1@ %s" % self._settings_str)
        assert "Le sous-projet vous salut" in self.t.out
