# tests.test_cmake

from io          import StringIO
from os.path     import join as pjoin, splitext
from unittest    import TestCase

import itertools

from bdemeta.cmake import parse_args, generate_bde, generate
from bdemeta.types import Target, Package, CMake, Pkg

from tests.cmake_parser import lex, find_command, parse

def get_filestore_writer(files):
    def write(path, writer):
        files[path] = StringIO()
        writer(files[path])
        files[path].seek(0)
    return write

def grouper(iterable, n, fillvalue=None):
    "Collect data into fixed-length chunks or blocks"
    # grouper('ABCDEFG', 3, 'x') --> ABC DEF Gxx"
    args = [iter(iterable)] * n
    return itertools.zip_longest(*args, fillvalue=fillvalue)

class ParseArgsTest(TestCase):
    def test_one_target(self):
        options, targets = parse_args(['foo'])
        assert(set()   == options)
        assert(['foo'] == targets)

    def test_four_targets(self):
        options, targets = parse_args(['foo', 'bar', 'bam', 'baz'])
        assert(set()                        == options)
        assert(['foo', 'bar', 'bam', 'baz'] == targets)

    def test_generate_one_test(self):
        options, targets = parse_args(['-t', 'foo'])
        assert({'foo'} == options)
        assert([]      == targets)

    def test_generate_one_test_longform(self):
        options, targets = parse_args(['--generate-test', 'foo'])
        assert({'foo'} == options)
        assert([]      == targets)

    def test_generate_one_test_longform_equals(self):
        options, targets = parse_args(['--generate-test=foo'])
        assert({'foo'} == options)
        assert([]      == targets)

class GenerateTargetTest(TestCase):
    def _check_target_no_test(self, cmake, name, path, deps, components):
        _, command = find_command(cmake, 'add_library')
        assert(name == command[0])
        for index, component in enumerate(components):
            assert(component['source'] == command[index + 1])

        _, command = find_command(cmake, 'target_include_directories')
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

        _, command = find_command(cmake, 'install', ['FILES'])
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
        for driver, commands in zip(drivers, grouper(cmake, 2)):
            exec_command, link_command = commands
            assert('add_executable' == exec_command[0])
            assert(splitext(driver)[0] == exec_command[1][0])
            assert(driver              == exec_command[1][1])

            assert('target_link_libraries' == link_command[0])
            assert(splitext(driver)[0]     == link_command[1][0])
            assert(name                    == link_command[1][1])

    def _check_target_deps(self, cmake, name, dependencies):
        _, command = find_command(cmake, 'target_link_libraries')
        assert(name     == command[0])
        assert('PUBLIC' == command[1])
        for index, dep in enumerate(dependencies):
            assert(dep == command[index + 2])

    def _get_testing(self, cmake):
        testing_start, _ = find_command(cmake, 'if', ['BUILD_TESTING'])
        return parse(iter(cmake[testing_start+1:]))

    def _check_package(self, cmake, name, path, deps, comps, is_test):
        self._check_target_no_test(cmake, name, path, deps, comps)
        if is_test:
            self._check_target_drivers(self._get_testing(cmake), name, comps)

    def _test_package(self, name, path, deps, comps, is_test):
        target = Package(path, deps, comps)

        files = {}
        generate([target],
                 get_filestore_writer(files),
                 {target.name} if is_test else {})

        assert(f'{name}.cmake' in files)
        generated = files[f'{name}.cmake']

        cmake = list(lex(generated))
        self._check_package(cmake, name, path, deps, comps, is_test)

    def test_base_target_causes_error(self):
        target = Target('t', [])

        files  = {}
        caught = False
        try:
            generate([target], get_filestore_writer(files), {})
        except RuntimeError:
            caught = True
        assert(caught)

    def test_empty_package_no_deps_no_test(self):
        self._test_package('target', pjoin('path', 'target'), [], [], False)

    def test_one_comp_package_no_deps_no_test(self):
        comps = [{ 'header': 'file.h',
                   'source': 'file.cpp',
                   'driver': 'file.t.cpp' }]
        self._test_package('target', pjoin('path', 'target'), [], comps, False)

    def test_one_comp_package_no_deps_test(self):
        comps = [{ 'header': 'file.h',
                   'source': 'file.cpp',
                   'driver': 'file.t.cpp' }]
        self._test_package('target', pjoin('path', 'target'), [], comps, True)

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

        files = {}
        generate([p1, p2], get_filestore_writer(files), {})

        assert('p1.cmake' in files)
        assert('p2.cmake' in files)
        generated1 = files['p1.cmake']
        generated2 = files['p2.cmake']

        cmake1 = list(lex(generated1))
        self._check_package(cmake1, 'p1', 'p1', deps1, comps1, is_test)
        cmake2 = list(lex(generated2))
        self._check_package(cmake2, 'p2', 'p2', deps2, comps2, is_test)

        assert('CMakeLists.txt' in files)
        assert('include(p1.cmake)' in files['CMakeLists.txt'].getvalue())
        assert('include(p2.cmake)' in files['CMakeLists.txt'].getvalue())

    def test_empty_package_with_override(self):
        p = Package('p', [], [])
        p.overrides = 'override.cmake'

        files = {}
        generate([p], get_filestore_writer(files), {})

        assert('CMakeLists.txt' in files)
        assert(f'include({p.overrides})' in files['CMakeLists.txt'].getvalue())

    def test_empty_package_with_no_output_dep(self):
        p1 = Package('p1', [],   [])
        p2 = Package('p2', [p1], [])
        p1.has_output = False

        files = {}
        generate([p1, p2], get_filestore_writer(files), {})

        cmake = list(lex(files['p2.cmake']))
        _, libs = find_command(cmake, 'target_link_libraries')
        assert('p1' not in libs)

    def test_empty_package_lazily_bound(self):
        p = Package('p', [], [])
        p.lazily_bound = True

        files = {}
        generate([p], get_filestore_writer(files), {})

        assert('p.cmake' in files)
        commands = list(lex(files['p.cmake']))

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
        c = CMake('bar', path)

        files = {}
        generate([c], get_filestore_writer(files), {})

        assert('CMakeLists.txt' in files)
        cmake = files['CMakeLists.txt'].getvalue()

        # Note: CMake supports '/' for path separators on Windows (in addition
        # to Unix), so for simplicity we use '/' universally
        upath = path.replace('\\', '/')
        assert(f'add_subdirectory({upath} {c.name})' in cmake)

    def test_no_pkg_config_no_include(self):
        c = CMake('foo', 'bar')

        files = {}
        generate([c], get_filestore_writer(files), {})

        assert('CMakeLists.txt' in files)
        cmake = files['CMakeLists.txt'].getvalue()

        assert('include(FindPkgConfig)' not in cmake)

    def test_pkg_config_has_include(self):
        p = Pkg('foo', 'bar')

        files = {}
        generate([p], get_filestore_writer(files), {})

        assert('CMakeLists.txt' in files)
        cmake = files['CMakeLists.txt'].getvalue()

        assert('include(FindPkgConfig)' in cmake)

    def test_pkg_config_generates_cmake(self):
        name    = 'foo'
        package = 'bar'
        p = Pkg(name, package)

        files = {}
        generate([p], get_filestore_writer(files), {})

        assert('CMakeLists.txt' in files)
        cmake = files['CMakeLists.txt'].getvalue()

        assert(f'{name}.cmake' in files)
        assert(f'include({name}.cmake)' in cmake)

    def test_pkg_config_generates_search(self):
        name    = 'foo'
        package = 'bar'
        p = Pkg(name, package)

        files = {}
        generate([p], get_filestore_writer(files), {})

        cmake = files[f'{name}.cmake'].getvalue()
        assert(f'pkg_check_modules({name} REQUIRED {package})' in cmake)

    def test_pkg_config_generates_interface_lib(self):
        name    = 'foo'
        package = 'bar'
        p = Pkg(name, package)

        files = {}
        generate([p], get_filestore_writer(files), {})

        cmake = list(lex(files[f'{name}.cmake']))
        _, command = find_command(cmake, 'add_library')
        assert(name == command[0])
        assert('INTERFACE' == command[1])

    def test_pkg_config_generates_shared_props(self):
        name    = 'foo'
        package = 'bar'
        p = Pkg(name, package)

        files = {}
        generate([p], get_filestore_writer(files), {})

        cmake = files[f'{name}.cmake']
        commands = list(lex(cmake))
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
        p = Pkg(name, package)

        files = {}
        generate([p], get_filestore_writer(files), {})

        cmake = files[f'{name}.cmake']
        commands = list(lex(cmake))
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

