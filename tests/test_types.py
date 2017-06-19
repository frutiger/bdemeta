# tests.test_types

from os.path import join as pj
from unittest import TestCase

from bdemeta.types import Package, Group

class TestPackage(TestCase):
    def test_str_ness(self):
        p = Package(pj('path', 'to', 'foo'), ['bar'], 'baz', 'bam')
        assert('foo' == p)

    def test_dependencies(self):
        p = Package(pj('path', 'to', 'foo'), ['bar'], 'baz', 'bam')
        assert(['bar'] == p.dependencies())

    def test_components(self):
        p = Package(pj('path', 'to', 'foo'), ['bar'], 'baz', 'bam')
        assert('baz' == p.components())

    def test_includes(self):
        path = pj('path', 'to', 'foo')
        p = Package(path, ['bar'], 'baz', 'bam')
        assert([path] == list(p.includes()))

class TestGroup(TestCase):
    def test_str_ness(self):
        g = Group(pj('path', 'g'), [], [])
        assert('g' == g)

    def test_no_package_includes(self):
        g = Group(pj('path', 'g'), [], [])
        assert([] == list(g.includes()))

    def test_one_package_includes(self):
        p_path = pj('path', 'g', 'p')
        g_path = pj('path', 'g')
        p = Package(p_path, [], [], 'bam')
        g = Group(  g_path, [], [p])
        assert([p_path] == list(g.includes()))

    def test_two_package_cflags(self):
        p1_path = pj('path', 'g', 'p1')
        p2_path = pj('path', 'g', 'p2')
        g_path = pj('path', 'g')
        p1 = Package(p1_path, [],   [], 'bam')
        p2 = Package(p2_path, [p1], [], 'bam')
        g = Group(g_path, [], [p2, p1])
        assert([p2_path, p1_path] == list(g.includes()))

    def test_sources_one_cpp_component_no_driver(self):
        c1_path = pj('path', 'g', 'p1', 'gp1_c1.cpp')
        p1_path = pj('path', 'g', 'p1')
        g_path  = pj('path', 'g')
        p1 = Package(p1_path, [], [c1_path], 'bam')
        g  = Group(g_path, [], [p1])

        assert([c1_path] == list(g.sources()))

    def test_sources_one_c_component_no_driver(self):
        c1_path = pj('path', 'g', 'p1', 'gp1_c1.c')
        p1_path = pj('path', 'g', 'p1')
        g_path  = pj('path', 'g')
        p1 = Package(p1_path, [], [c1_path], 'bam')
        g  = Group(g_path, [], [p1])

        assert([c1_path] == list(g.sources()))

    def test_sources_one_cpp_component_with_driver(self):
        c1_path   = pj('path', 'g', 'p1', 'gp1_c1.cpp')
        c1_driver = pj('path', 'g', 'p1', 'gp1_c1.t.cpp')
        p1_path = pj('path', 'g', 'p1')
        g_path  = pj('path', 'g')
        p1 = Package(p1_path, [], [c1_path], [c1_driver])
        g  = Group(g_path, [], [p1])

        assert([c1_path]   == list(g.sources()))
        assert([c1_driver] == list(g.drivers()))

