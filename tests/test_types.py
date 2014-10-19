# tests.test_types

from unittest import TestCase

from bdemeta.types import Component, Source, Buildable, Node, Unit
from bdemeta.types import Package, Target, Group, Application

class TestUnit(TestCase):
    def test_cflags(self):
        u = Unit('foo', ['bar'], 'bam', 'baz')
        assert('baz' == u.cflags())

class TestPackage(TestCase):
    in_cflags = ['a']
    ex_cflags = ['b']

    def test_str_ness(self):
        p = Package('path/to/foo',
                    ['bar'],
                    self.in_cflags,
                    self.ex_cflags,
                    'baz')
        assert('foo' == p)

    def test_internal_cflags(self):
        p = Package('path/to/foo',
                    ['bar'],
                    self.in_cflags,
                    self.ex_cflags,
                    'baz')
        assert(['a'] == p.internal_cflags())

    def test_dependencies(self):
        p = Package('path/to/foo',
                    ['bar'],
                    self.in_cflags,
                    self.ex_cflags,
                    'baz')
        assert(['bar'] == p.dependencies())

    def test_cflags(self):
        p = Package('path/to/foo',
                    ['bar'],
                    self.in_cflags,
                    self.ex_cflags,
                    'baz')
        # note that the package path comes after the user-specified cflags
        assert(['b', '-Ipath/to/foo'] == p.external_cflags())

    def test_empty_ld_args(self):
        p = Package('path/to/foo',
                    ['bar'],
                    self.in_cflags,
                    self.ex_cflags,
                    'baz')
        assert([] == p.ld_args())

    def test_empty_ld_input(self):
        p = Package('path/to/foo',
                    ['bar'],
                    self.in_cflags,
                    self.ex_cflags,
                    'baz')
        assert([] == p.ld_input())

    def test_components(self):
        p = Package('path/to/foo',
                    ['bar'],
                    self.in_cflags,
                    self.ex_cflags,
                    'baz')
        assert('baz' == p.components())

class TestTarget(TestCase):
    in_cflags = ['a']
    ex_cflags = ['b']

    def test_str_ness(self):
        t = Target('foo',
                   ['bar'],
                   self.in_cflags,
                   self.ex_cflags,
                   ['bam'],
                   ['baz'],
                   'zing')
        assert('foo' == t)

    def test_internal_cflags(self):
        t = Target('foo',
                   ['bar'],
                   self.in_cflags,
                   self.ex_cflags,
                   ['bam'],
                   ['baz'],
                   'zing')
        assert(['a'] == t.internal_cflags())

    def test_external_cflags(self):
        t = Target('foo',
                   ['bar'],
                   self.in_cflags,
                   self.ex_cflags,
                   ['bam'],
                   ['baz'],
                   'zing')
        assert(['b'] == t.external_cflags())

    def test_dependencies(self):
        t = Target('foo',
                   ['bar'],
                   self.in_cflags,
                   self.ex_cflags,
                   ['bam'],
                   ['baz'],
                   'zing')
        assert(['bar'] == t.dependencies())

    def test_cflags(self):
        t = Target('foo',
                   ['bar'],
                   self.in_cflags,
                   self.ex_cflags,
                   ['bam'],
                   ['baz'],
                   'zing')
        assert(['b'] == t.cflags())

    def test_sources(self):
        t = Target('foo',
                   ['bar'],
                   self.in_cflags,
                   self.ex_cflags,
                   ['bam'],
                   ['baz'],
                   'zing')
        assert(['bam'] == t.sources())

    def test_ld_args(self):
        t = Target('foo',
                   ['bar'],
                   self.in_cflags,
                   self.ex_cflags,
                   ['bam'],
                   ['baz'],
                   'zing')
        assert(['baz'] == t.ld_args())

    def test_output(self):
        t = Target('foo',
                   ['bar'],
                   self.in_cflags,
                   self.ex_cflags,
                   ['bam'],
                   ['baz'],
                   'zing')
        assert('zing' == t.output())

    def test_ld_input(self):
        t = Target('foo',
                   ['bar'],
                   self.in_cflags,
                   self.ex_cflags,
                   ['bam'],
                   ['baz'],
                   'zing')
        # note that the output comes before the user-specified ld_args
        assert(['zing', 'baz'] == t.ld_input())

class TestGroup(TestCase):
    in_cflags = ['a']
    ex_cflags = ['b']

    def test_str_ness(self):
        g = Group('path/g', [], self.in_cflags, self.ex_cflags, [], [])
        assert('g' == g)

    def test_no_package_cflags(self):
        g = Group('path/g', [], self.in_cflags, self.ex_cflags, [], [])
        assert(['b'] == g.cflags())  # g  external cflag

    def test_one_package_cflags(self):
        p = Package('path/g/p', [], self.in_cflags, self.ex_cflags, [])
        g = Group('path/g',     [], self.in_cflags, self.ex_cflags, [p], [])
        assert(['b',                          # g external cflag
                'b',                          # p external cflag
                '-Ipath/g/p'] == g.cflags())  # p package  cflag

    def test_two_package_cflags(self):
        p1 = Package('path/g/p1', [],   self.in_cflags, self.ex_cflags, [])
        p2 = Package('path/g/p2', [p1], self.in_cflags, self.ex_cflags, [])
        g = Group('path/g', [], self.in_cflags, self.ex_cflags, [p2, p1], [])
        assert(['b',                           # g  internal cflag
                'b',                           # p2 internal cflag
                '-Ipath/g/p2',                 # p2 package  cflag
                'b',                           # p1 internal cflag
                '-Ipath/g/p1'] == g.cflags())  # p1 package  cflag

    def test_output(self):
        g = Group('path/g', [], self.in_cflags, self.ex_cflags, [], [])
        assert('out/libs/libg.a' == g.output())

    def test_sources_one_cpp_component_no_driver(self):
        c1 = Component('gp1_c1', 'path/g/p1/gp1_c1.cpp', None)
        p1 = Package('path/g/p1', [], self.in_cflags, self.ex_cflags, [c1])
        g  = Group('path/g', [], self.in_cflags, self.ex_cflags, [p1], ['baz'])

        assert(1 == len(g.sources()))
        s = g.sources()[0]
        assert('object'               == s.type)
        assert('gp1_c1.o'             == s.name)
        assert('path/g/p1/gp1_c1.cpp' == s.input)
        assert('cxx'                  == s.compiler)
        assert(' a' +                              # g internal cflag
               ' b' +                              # g external cflag
               ' a' +                              # p internal cflag
               ' b' +                              # p external cflag
               ' -Ipath/g/p1'         == s.flags)  # p package  cflag
        assert('out/objs/gp1_c1.o'    == s.output)

    def test_sources_one_c_component_no_driver(self):
        c1 = Component('gp1_c1', 'path/g/p1/gp1_c1.c', None)
        p1 = Package('path/g/p1', [], self.in_cflags, self.ex_cflags, [c1])
        g  = Group('path/g', [], self.in_cflags, self.ex_cflags, [p1], ['baz'])

        assert(1 == len(g.sources()))
        s = g.sources()[0]
        assert('object'             == s.type)
        assert('gp1_c1.o'           == s.name)
        assert('path/g/p1/gp1_c1.c' == s.input)
        assert('cc'                 == s.compiler)
        assert(' a' +                            # g internal cflag
               ' b' +                            # g external cflag
               ' a' +                            # p internal cflag
               ' b' +                            # p external cflag
               ' -Ipath/g/p1'       == s.flags)  # p package  cflag
        assert('out/objs/gp1_c1.o'  == s.output)

    def test_sources_one_cpp_component_with_driver(self):
        c1 = Component('gp1_c1',
                       'path/g/p1/gp1_c1.cpp',
                       'path/g/p1/gp1_c1.t.cpp')
        p1 = Package('path/g/p1', [], self.in_cflags, self.ex_cflags, [c1])
        g  = Group('path/g', [], self.in_cflags, self.ex_cflags, [p1], ['baz'])

        assert(2 == len(g.sources()))

        s1 = g.sources()[0]
        assert('object'               == s1.type)
        assert('gp1_c1.o'             == s1.name)
        assert('path/g/p1/gp1_c1.cpp' == s1.input)
        assert('cxx'                  == s1.compiler)
        assert(' a' +                               # g internal cflag
               ' b' +                               # g external cflag
               ' a' +                               # p internal cflag
               ' b' +                               # p external cflag
               ' -Ipath/g/p1'         == s1.flags)  # p package  cflag
        assert('out/objs/gp1_c1.o'    == s1.output)

        s2 = g.sources()[1]
        assert('executable'             == s2.type)
        assert('gp1_c1.t'               == s2.name)
        assert('path/g/p1/gp1_c1.t.cpp ' +             # driver
               'out/libs/libg.a '        +             # dependent library
               'baz'                    == s2.input)  # g ld_dep
        assert('cxx'                    == s2.compiler)
        assert(' a' +                                 # g internal cflag
               ' b' +                                 # g external cflag
               ' a' +                                 # p internal cflag
               ' b' +                                 # p external cflag
               ' -Ipath/g/p1'           == s2.flags)  # p package  cflag
        assert('out/tests/gp1_c1.t'     == s2.output)

class TestApplication(TestCase):
    in_cflags = ['a']
    ex_cflags = ['b']

    def test_str_ness(self):
        a = Application('path/a', [], self.in_cflags, self.ex_cflags, [])
        assert('a' == a)

    def test_sources_no_dep(self):
        a = Application('path/m_a',
                        [],
                        self.in_cflags,
                        self.ex_cflags,
                        ['baz'])

        assert(1 == len(a.sources()))
        s = a.sources()[0]
        assert('executable'       == s.type)
        assert('m_a'              == s.name)
        assert('path/m_a/a.m.cpp ' +           # a source
               'baz'              == s.input)  # a ld_dep
        assert('cxx'              == s.compiler)
        assert(' a' +                          # a internal cflag
               ' b'               == s.flags)  # a external cflag
        assert('out/apps/m_a'     == s.output)

