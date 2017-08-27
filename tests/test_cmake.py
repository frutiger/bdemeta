# tests.test_cmake

from io          import StringIO
from os.path     import join as pjoin, splitext
from unittest    import TestCase

import itertools
import re

from bdemeta.cmake import parse_args, generate_target, generate
from bdemeta.types import Target, Package, CMake

def parse_cmake(input):
    whitespace = re.compile('\s+')

    parsing_item    = False
    parsing_command = False
    command, args   = '', []
    while True:
        char = input.read(1)
        if char is '':
            break
        if whitespace.match(char):
            if parsing_item:
                if parsing_command:
                    args.append('')
                else:
                    command += char
            parsing_item = False
        elif char == '(':
            if parsing_command:
                raise RuntimeError('Nested command')
            args.append('')
            parsing_command = True
            parsing_item    = False
        elif char == ')':
            if not parsing_command:
                raise RuntimeError('Unexpected ")"')
            if args[-1] == '':
                args = args[:-1]
            yield command, args
            command, args   = '', []
            parsing_item    = False
            parsing_command = False
        else:
            if parsing_command:
                args[-1] += char
            else:
                command += char
            parsing_item = True

def get_filestore_writer(files):
    def write(path, writer):
        files[path] = StringIO()
        writer(files[path])
        files[path].seek(0)
    return write

def partial_match(lhs, rhs):
    if lhs[0] != rhs[0]:
        return False

    return all(map(lambda x: x[0] == x[1], zip(lhs[1], rhs[1])))

def find_command(cmake, command, args=None):
    args = [] if args is None else args

    candidates = []
    for index, item in enumerate(cmake):
        if partial_match((command, args), item):
            candidates.append((index, item[1]))

    if len(candidates) == 0:
        raise RuntimeError('Predicate ({}, {}) not found'.format(command,
                                                                 args))
    if len(candidates) > 1:
        raise RuntimeError('Ambiguous predicate ({}, {}) yielded {}'.format(
                                                                   command,
                                                                   args,
                                                                   candidates))
    return candidates[0]

def find_index_after(cmake, index, command):
    while index < len(cmake):
        if partial_match(cmake[index], (command, ())):
            return index
        index += 1

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
        assert(path     == command[2])

        _, command = find_command(cmake, 'target_link_libraries', [name])
        assert(name     == command[0])
        assert('PUBLIC' == command[1])
        for index, dep in enumerate(deps):
            assert(dep == command[index + 2])

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
        testing_end      = find_index_after(cmake, testing_start, 'endif')
        return cmake[testing_start+1:testing_end]

    def _check_package(self, cmake, name, path, deps, comps, is_test):
        self._check_target_no_test(cmake, name, path, deps, comps)
        if is_test:
            self._check_target_drivers(self._get_testing(cmake), name, comps)

    def _test_package(self, name, path, deps, comps, is_test):
        target = Package(path, deps, comps)

        files = {}
        generate_target(target, get_filestore_writer(files), is_test)

        assert(f'{name}.cmake' in files)
        generated = files[f'{name}.cmake']

        cmake = list(parse_cmake(generated))
        self._check_package(cmake, name, path, deps, comps, is_test)

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

        cmake1 = list(parse_cmake(generated1))
        self._check_package(cmake1, 'p1', 'p1', deps1, comps1, is_test)
        cmake2 = list(parse_cmake(generated2))
        self._check_package(cmake2, 'p2', 'p2', deps2, comps2, is_test)

        assert('CMakeLists.txt' in files)
        assert('include(p1.cmake)' in files['CMakeLists.txt'].getvalue())
        assert('include(p2.cmake)' in files['CMakeLists.txt'].getvalue())

    def test_cmake_target(self):
        path = pjoin('foo', 'bar')
        c = CMake('bar', path)

        files = {}
        generate([c], get_filestore_writer(files), {})

        assert('CMakeLists.txt' in files)
        cmake = files['CMakeLists.txt'].getvalue()
        assert(f'add_subdirectory({path} {c})' in cmake)

