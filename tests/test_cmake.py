# tests.test_cmake

from io          import StringIO
from os.path     import join as pjoin, splitext
from unittest    import TestCase

import itertools

from bdemeta.cmake import generate
from bdemeta.types import Application, CMake, Package, Pkg, Target

from tests.cmake_parser import lex, find_commands, find_command, parse

def grouper(iterable, n, fillvalue=None):
    "Collect data into fixed-length chunks or blocks"
    # grouper('ABCDEFG', 3, 'x') --> ABC DEF Gxx"
    args = [iter(iterable)] * n
    return itertools.zip_longest(*args, fillvalue=fillvalue)

class GenerateTargetTest(TestCase):
    def _check_target_no_test(self, cmake, name, path, deps, components):
        _, command = find_command(cmake, 'add_library', [name])
        assert(name == command[0])
        for index, component in enumerate(components):
            assert(component['source'] == command[index + 1])

        _, command = find_command(cmake, 'target_include_directories', [name])
        assert(name     == command[0])
        assert('PUBLIC' == command[1])

        # Note: CMake supports '/' for path separators on Windows (in addition
        # to Unix), so for simplicity we use '/' universally
        upath = path.replace('\\', '/')
        assert(upath    == command[2])

        _, command = find_command(cmake, 'target_link_libraries', [name])
        assert(name     == command[0])
        assert('PUBLIC' == command[1])
        for index, dep in enumerate(deps):
            assert(dep.name == command[index + 2])

        for _, command in find_commands(cmake, 'install', ['FILES']):
            assert('FILES'       == command[0])
            headers = [c['header'] for c in components if c['header'] != None]
            index = 1
            for header in headers:
                assert(header == command[index])
                index += 1
            assert('DESTINATION' == command[index + 0])
            assert('include'     == command[index + 1])

        _, command = find_command(cmake, 'install', ['TARGETS',
                                                     name,
                                                     'COMPONENT',
                                                     'development'])
        assert('TARGETS'     == command[0])
        assert(name          == command[1])
        assert('COMPONENT'   == command[2])
        assert('development' == command[3])
        assert('DESTINATION' == command[4])
        assert('lib'         == command[5])

        _, command = find_command(cmake, 'install', ['TARGETS',
                                                     name,
                                                     'COMPONENT',
                                                     'runtime'])
        assert('TARGETS'     == command[0])
        assert(name          == command[1])
        assert('COMPONENT'   == command[2])
        assert('runtime'     == command[3])
        assert('DESTINATION' == command[4])
        assert('.'           == command[5])

    def _check_target_drivers(self, cmake, name, components):
        drivers = [c['driver'] for c in components if c['driver'] != None]
        for driver in drivers:
            executable = splitext(driver)[0]
            _, command = find_command(cmake, 'add_executable', [executable])
            assert('EXCLUDE_FROM_ALL' == command[1])
            assert(driver             == command[2])

            executable = splitext(driver)[0]
            _, command = find_command(cmake,
                                      'target_link_libraries',
                                      [executable])
            assert(name == command[1])

    def _check_test_target(self, cmake, name, components):
        drivers = [c['driver'] for c in components if c['driver'] != None]
        if len(drivers):
            find_command(cmake, 'add_custom_target', [name + '.t'])
        else:
            with self.assertRaises(LookupError):
                find_command(cmake, 'add_custom_target', [name + '.t'])

    def _check_target_deps(self, cmake, name, dependencies):
        _, command = find_command(cmake, 'target_link_libraries')
        assert(name     == command[0])
        assert('PUBLIC' == command[1])
        for index, dep in enumerate(dependencies):
            assert(dep == command[index + 2])

    def _check_package(self, cmake, name, path, deps, comps):
        self._check_target_no_test(cmake, name, path, deps, comps)
        self._check_target_drivers(cmake, name, comps)
        self._check_test_target(cmake, name, comps)

    def _test_package(self, name, path, deps, comps, has_tests):
        target = Package(path, deps, comps)

        out = StringIO()
        generate([target], out)

        cmake = list(lex(out))

        self._check_package(cmake, name, path, deps, comps)

        if has_tests:
            find_command(cmake, 'add_custom_target', ['tests'])
        else:
            with self.assertRaises(LookupError):
                find_command(cmake, 'add_custom_target', ['tests'])

    def test_base_target_no_deps(self):
        t = Target('t', [])

        out = StringIO()
        generate([t], out)

        assert(out.getvalue())

    def test_cmake_prologue(self):
        t = Target('t', [])

        out = StringIO()
        generate([t], out)

        cmake = list(lex(out))

        find_command(cmake, 'cmake_minimum_required')
        find_command(cmake, 'project')

    def test_empty_package_no_deps_no_test(self):
        self._test_package('target', pjoin('path', 'target'), [], [], False)

    def test_one_comp_package_no_deps_no_test(self):
        comps = [{ 'header': 'file.h',
                   'source': 'file.cpp',
                   'driver': None }]
        self._test_package('target', pjoin('path', 'target'), [], comps, False)

    def test_application(self):
        name  = 'app'
        path  = pjoin('path', 'app')
        deps = [Target('foo', [])]
        comps = [{ 'header': None,
                   'source': 'file.m.cpp',
                   'driver': None }]

        target = Application(path, deps, comps)

        out = StringIO()
        generate([target], out)

        cmake = list(lex(out))

        find_command(cmake, 'add_executable', [name, f'file.m.cpp'])
        find_command(cmake, 'target_link_libraries', [name, 'PUBLIC', 'foo'])

    def test_one_comp_package_no_deps_test(self):
        comps = [{ 'header': 'file.h',
                   'source': 'file.cpp',
                   'driver': 'file.t.cpp' }]
        self._test_package('target', pjoin('path', 'target'), [], comps, True)

    def test_one_comp_package_no_deps_plugin_test(self):
        comps = [{ 'header': 'file.h',
                   'source': 'file.cpp',
                   'driver': 'file.t.cpp' }]
        target = Package(pjoin('path', 'target'), [], comps)
        target.plugin_tests = True

        out = StringIO()
        generate([target], out)

        cmake = list(lex(out))

        find_command(cmake, 'add_library', ['file.t', 'SHARED'])
        find_command(cmake, 'target_link_libraries', ['file.t', 'target'])

        apple_start, _ = find_command(cmake, 'if', ['APPLE'])
        stmts = parse(iter(cmake[apple_start:]))[0]
        _, props = find_command(stmts[1], 'set_target_properties')

        assert(['file.t',
                'PROPERTIES',
                'LINK_FLAGS',
                '"-undefined',
                'dynamic_lookup"'] == props)

        win32_start, _ = find_command(cmake, 'if', ['WIN32'])
        stmts = parse(iter(cmake[win32_start:]))[0]

        _, props = find_command(stmts[1], 'target_link_options')
        assert(['file.t', 'PUBLIC', '/EXPORT:main'] == props)

    def test_empty_package_one_dep_no_test(self):
        deps = [Target('foo', [])]
        self._test_package('target', pjoin('path', 'target'), deps, [], False)

    def test_two_empty_packages_no_deps_no_test(self):
        deps1  = []
        comps1 = []
        p1 = Package('p1', deps1, comps1)

        deps2  = []
        comps2 = []
        p2 = Package('p2', deps2, comps2)

        is_test = False

        out = StringIO()
        generate([p1, p2], out)

        cmake = list(lex(out))
        self._check_package(cmake, 'p1', 'p1', deps1, comps1)
        self._check_package(cmake, 'p2', 'p2', deps2, comps2)

    def test_empty_package_with_override(self):
        p = Package('p', [], [])
        p.overrides = 'override.cmake'

        out = StringIO()
        generate([p], out)

        assert(f'include({p.overrides})' in out.getvalue())

    def test_empty_package_with_no_output_dep(self):
        p1 = Package('p1', [],   [])
        p2 = Package('p2', [p1], [])
        p1.has_output = False

        out = StringIO()
        generate([p1, p2], out)

        cmake = list(lex(out))
        _, libs = find_command(cmake, 'target_link_libraries', ['p2'])
        assert('p1' not in libs)

    def test_empty_package_lazily_bound(self):
        p = Package('p', [], [])
        p.lazily_bound = True

        out = StringIO()
        generate([p], out)

        commands = list(lex(out))

        apple_start, _ = find_command(commands, 'if', ['APPLE'])
        stmts = parse(iter(commands[apple_start:]))[0]

        _, props = find_command(stmts[1], 'set_target_properties')
        assert(['p',
                'PROPERTIES',
                'LINK_FLAGS',
                '"-undefined',
                'dynamic_lookup"'] == props)

    def test_cmake_target(self):
        path = pjoin('foo', 'bar')
        c = CMake('bar', path, [])

        out = StringIO()
        generate([c], out)

        # Note: CMake supports '/' for path separators on Windows (in addition
        # to Unix), so for simplicity we use '/' universally
        upath = path.replace('\\', '/')
        assert(f'add_subdirectory({upath} {c.name})' in out.getvalue())

    def test_no_pkg_config_no_include(self):
        c = CMake('foo', 'bar', [])

        out = StringIO()
        generate([c], out)

        assert('include(FindPkgConfig)' not in out.getvalue())

    def test_pkg_config_has_include(self):
        p = Pkg('foo', 'bar', [])

        out = StringIO()
        generate([p], out)

        assert('include(FindPkgConfig)' in out.getvalue())

    def test_pkg_config_generates_cmake(self):
        name    = 'foo'
        package = 'bar'
        p = Pkg(name, package, [])

        out = StringIO()
        generate([p], out)

        assert(out.getvalue())

    def test_pkg_config_generates_search(self):
        name    = 'foo'
        package = 'bar'
        p = Pkg(name, package, [])

        out = StringIO()
        generate([p], out)

        cmake = out.getvalue()
        assert(f'pkg_check_modules({name} REQUIRED {package})' in cmake)

    def test_pkg_config_generates_interface_lib(self):
        name    = 'foo'
        package = 'bar'
        p = Pkg(name, package, [])

        out = StringIO()
        generate([p], out)

        cmake = list(lex(out))
        _, command = find_command(cmake, 'add_library')
        assert(name == command[0])
        assert('INTERFACE' == command[1])

    def test_pkg_config_generates_shared_props(self):
        name    = 'foo'
        package = 'bar'
        p = Pkg(name, package, [])

        out = StringIO()
        generate([p], out)

        commands = list(lex(out))
        sh_lib_start, _ = find_command(commands, 'if', ['BUILD_SHARED_LIBS'])
        stmts = parse(iter(commands[sh_lib_start:]))[0]

        shared = { tuple(stmt[0]): (stmt[1], stmt[2]) for stmt in stmts[1] }

        assert((f'{name}_INCLUDE_DIRS',) in shared)
        includes = shared[(f'{name}_INCLUDE_DIRS',)]
        assert([] == includes[1])
        assert(1 == len(includes[0]))
        include = includes[0][0]
        assert('target_include_directories' == include[0])
        assert([name, 'INTERFACE', f'"${{{name}_INCLUDE_DIRS}}"'] == \
                                                                    include[1])

        assert((f'{name}_LDFLAGS',) in shared)
        ldflags = shared[(f'{name}_LDFLAGS',)]
        assert([] == ldflags[1])
        assert(1 == len(ldflags[0]))
        ldflag = ldflags[0][0]
        assert('target_link_libraries' == ldflag[0])
        assert([name, 'INTERFACE', f'"${{{name}_LDFLAGS}}"'] == ldflag[1])

        assert((f'{name}_CFLAGS_OTHER',) in shared)
        cflags = shared[(f'{name}_CFLAGS_OTHER',)]
        assert([] == cflags[1])
        assert(1 == len(cflags[0]))
        cflag = cflags[0][0]
        assert('target_compile_options' == cflag[0])
        assert([name, 'INTERFACE', f'"${{{name}_CFLAGS_OTHER}}"'] == cflag[1])

    def test_pkg_config_generates_static_props(self):
        name    = 'foo'
        package = 'bar'
        p = Pkg(name, package, [])

        out = StringIO()
        generate([p], out)

        commands = list(lex(out))
        sh_lib_start, _ = find_command(commands, 'if', ['BUILD_SHARED_LIBS'])
        stmts = parse(iter(commands[sh_lib_start:]))[0]

        static = { tuple(stmt[0]): (stmt[1], stmt[2]) for stmt in stmts[2] }

        assert((f'{name}_STATIC_INCLUDE_DIRS',) in static)
        includes = static[(f'{name}_STATIC_INCLUDE_DIRS',)]
        assert([] == includes[1])
        assert(1 == len(includes[0]))
        include = includes[0][0]
        assert('target_include_directories' == include[0])
        assert([name, 'INTERFACE', f'"${{{name}_STATIC_INCLUDE_DIRS}}"'] == \
                                                                    include[1])

        assert((f'{name}_STATIC_LDFLAGS',) in static)
        ldflags = static[(f'{name}_STATIC_LDFLAGS',)]
        assert([] == ldflags[1])
        assert(1 == len(ldflags[0]))
        ldflag = ldflags[0][0]
        assert('target_link_libraries' == ldflag[0])
        assert([name, 'INTERFACE', f'"${{{name}_STATIC_LDFLAGS}}"'] == \
                                                                     ldflag[1])

        assert((f'{name}_STATIC_CFLAGS_OTHER',) in static)
        cflags = static[(f'{name}_STATIC_CFLAGS_OTHER',)]
        assert([] == cflags[1])
        assert(1 == len(cflags[0]))
        cflag = cflags[0][0]
        assert('target_compile_options' == cflag[0])
        assert([name, 'INTERFACE', f'"${{{name}_STATIC_CFLAGS_OTHER}}"'] == \
                                                                      cflag[1])

