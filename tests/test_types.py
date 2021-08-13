# tests.test_types

from os.path import join as pj
from unittest import TestCase

from bdemeta.types import Target, Package, Group, CMake, Pkg, Identification

class TestIdentification(TestCase):
    def test_equal_ids(self):
        id1 = Identification('a')
        id2 = Identification('a')
        assert(id1 == id2)

    def test_unequal_ids(self):
        id1 = Identification('a')
        id2 = Identification('b')
        assert(id1 != id2)

    def test_compare_ids_with_non_ids(self):
        id1 = Identification('a')
        assert(id1 != 5)

class TestTarget(TestCase):
    def test_overrides_none(self):
        t = Target('foo', [])
        assert(None == t.overrides)

class TestPackage(TestCase):
    def test_name(self):
        p = Package(pj('path', 'to', 'foo'), ['bar'], [])
        assert('foo' == p.name)

    def test_dependencies(self):
        p = Package(pj('path', 'to', 'foo'), ['bar'], [])
        assert(['bar'] == p.dependencies())

    def test_headers(self):
        p = Package(pj('path', 'to', 'foo'), ['bar'], [{ 'header': 'baz'}])
        assert(['baz'] == list(p.headers()))

    def test_no_headers(self):
        p = Package(pj('path', 'to', 'foo'), ['bar'], [{ 'header': None }])
        assert([] == list(p.headers()))

    def test_sources(self):
        p = Package(pj('path', 'to', 'foo'), ['bar'], [{ 'source': 'baz'}])
        assert(['baz'] == list(p.sources()))

    def test_no_sources(self):
        p = Package(pj('path', 'to', 'foo'), ['bar'], [{ 'source': None }])
        assert([] == list(p.sources()))

    def test_drivers(self):
        p = Package(pj('path', 'to', 'foo'), ['bar'], [{ 'driver': 'baz'}])
        assert(['baz'] == list(p.drivers()))

    def test_no_drivers(self):
        p = Package(pj('path', 'to', 'foo'), ['bar'], [{ 'driver': None }])
        assert([] == list(p.drivers()))

    def test_includes(self):
        path = pj('path', 'to', 'foo')
        p = Package(path, ['bar'], 'baz')
        assert([path] == list(p.includes()))

    def test_not_executable(self):
        p = Package(pj('path', 'to', 'foo'), ['bar'], [])
        assert(False == p.executable)

    def test_executable(self):
        p = Package(pj('path', 'to', 'foo'), ['bar'], [], executable=True)
        assert(True == p.executable)

class TestGroup(TestCase):
    def test_name(self):
        g = Group(pj('path', 'g'), [], [])
        assert('g' == g.name)

    def test_no_package_includes(self):
        g = Group(pj('path', 'g'), [], [])
        assert([] == list(g.includes()))

    def test_one_package_includes(self):
        p_path = pj('path', 'g', 'p')
        g_path = pj('path', 'g')
        p = Package(p_path, [], [])
        g = Group(  g_path, [], [p])
        assert([p_path] == list(g.includes()))

    def test_two_package_includes(self):
        p1_path = pj('path', 'g', 'p1')
        p2_path = pj('path', 'g', 'p2')
        g_path = pj('path', 'g')
        p1 = Package(p1_path, [],   [])
        p2 = Package(p2_path, [p1], [])
        g = Group(g_path, [], [p2, p1])
        assert([p2_path, p1_path] == list(g.includes()))

    def test_sources_one_cpp_component_no_driver(self):
        c1_header = pj('path', 'g', 'p1', 'gp1_c1.h')
        c1_path   = pj('path', 'g', 'p1', 'gp1_c1.cpp')
        p1_path   = pj('path', 'g', 'p1')
        g_path    = pj('path', 'g')
        p1 = Package(p1_path, [], [{ 'header': c1_header,
                                     'source': c1_path,
                                     'driver': None,      }])
        g  = Group(g_path, [], [p1])

        assert([c1_path]   == list(g.sources()))
        assert([c1_header] == list(g.headers()))
        assert([]          == list(g.drivers()))

    def test_sources_one_c_component_no_driver(self):
        c1_path = pj('path', 'g', 'p1', 'gp1_c1.c')
        p1_path = pj('path', 'g', 'p1')
        g_path  = pj('path', 'g')
        p1 = Package(p1_path, [], [{ 'header': None,
                                     'source': c1_path,
                                     'driver': None, }])
        g  = Group(g_path, [], [p1])

        assert([c1_path] == list(g.sources()))

    def test_sources_one_cpp_component_with_driver(self):
        c1_header = pj('path', 'g', 'p1', 'gp1_c1.h')
        c1_path   = pj('path', 'g', 'p1', 'gp1_c1.cpp')
        c1_driver = pj('path', 'g', 'p1', 'gp1_c1.t.cpp')
        p1_path   = pj('path', 'g', 'p1')
        g_path    = pj('path', 'g')
        p1 = Package(p1_path, [], [{ 'header': c1_header,
                                     'source': c1_path,
                                     'driver': c1_driver, }])
        g  = Group(g_path, [], [p1])

        assert([c1_path]   == list(g.sources()))
        assert([c1_driver] == list(g.drivers()))

class TestCMake(TestCase):
    def test_name(self):
        c = CMake('c', pj('path', 'c'), [])
        assert('c' == c.name)

    def test_path(self):
        c = CMake('c', pj('path', 'c'), [])
        assert(pj('path', 'c') == c.path())

    def test_different_path(self):
        c = CMake('d', pj('path', 'c'), [])
        assert(pj('path', 'c') == c.path())

    def test_dependencies(self):
        c1 = CMake('c1', pj('path', 'c1'), [])
        c2 = CMake('c2', pj('path', 'c2'), [c1])
        assert(c1 in c2.dependencies())

class TestPkg(TestCase):
    def test_name(self):
        p = Pkg('p', None, [])
        assert('p' == p.name)

    def test_package_name(self):
        p = Pkg(None, 'foo', [])
        assert('foo' == p.package)

    def test_dependencies(self):
        p1 = Pkg('p1', 'p1', [])
        p2 = Pkg('p2', 'p2', [p1])
        assert(p1 in p2.dependencies())

