# tests.test_ninja

import collections
import io
import os
from unittest import TestCase

from bdemeta.types import Source
from bdemeta.ninja import generate

boilerplate = u'''\
rule cc-object
  deps    = gcc
  depfile = $out.d
  command = 1 -c $flags $in -MMD -MF $out.d -o $out

rule cxx-object
  deps    = gcc
  depfile = $out.d
  command = 2 -c $flags $in -MMD -MF $out.d -o $out

rule cxx-executable
  deps    = gcc
  depfile = $out.d
  command = 2 $flags $in -MMD -MF $out.d -o $out

rule ar
  command = 3 -crs $out $in

'''

class MockTarget(str):
    def __new__(cls, name, *args):
        return str.__new__(cls, name)

    def __init__(self, name, sources, objects, unit_tests, ld_args, output):
        self._name       = name
        self._sources    = sources
        self._objects    = objects
        self._unit_tests = unit_tests
        self._ld_args    = ld_args
        self._output     = output

    def sources(self):
        return self._sources

    def objects(self):
        return self._objects

    def unit_tests(self):
        return self._unit_tests

    def ld_args(self):
        return self._ld_args

    def output(self):
        return self._output

class TestGenerate(TestCase):
    def test_boilerplate(self):
        result = io.StringIO()
        generate((), {
            'cc':  '1',
            'c++': '2',
            'ar':  '3',
        }, result)
        assert(result.getvalue() == boilerplate)

    def test_target_one_object_no_executables(self):
        t = MockTarget('foo',
                       [Source('object',
                               'bar',
                               'bar.cpp',
                               'cxx',
                               ' -Ibam',
                               'bar.o')],
                       ['bar.o'],
                       [],
                       [],
                       'libfoo.a')
        result = io.StringIO()
        generate([t], {
            'cc':  '1',
            'c++': '2',
            'ar':  '3',
        }, result)
        assert(result.getvalue() == boilerplate + u'''\
build bar.o: cxx-object bar.cpp
  flags = -Ibam

build libfoo.a: ar bar.o

build foo: phony libfoo.a

default libfoo.a

''')

    def test_target_one_object_one_executable(self):
        t = MockTarget('foo',
                       [Source('object',
                               'foo_bar',
                               'foo/foo_bar.cpp',
                               'cxx',
                               ' -Ibam',
                               'objs/foo_bar.o'),
                        Source('executable',
                               'foo_bar.t',
                               'foo/foo_bar.t.cpp libs/libfoo.a',
                               'cxx',
                               ' -Ibam',
                               'tests/foo_bar.t')],
                       ['objs/foo_bar.o'],
                       ['tests/foo_bar.t'],
                       [],
                       'libs/libfoo.a')
        result = io.StringIO()
        generate([t], {
            'cc':  '1',
            'c++': '2',
            'ar':  '3',
        }, result)
        assert(result.getvalue() == boilerplate + u'''\
build objs/foo_bar.o: cxx-object foo/foo_bar.cpp
  flags = -Ibam

build tests/foo_bar.t: cxx-executable foo/foo_bar.t.cpp libs/libfoo.a
  flags = -Ibam

build foo_bar.t: phony tests/foo_bar.t

build libs/libfoo.a: ar objs/foo_bar.o

build foo: phony libs/libfoo.a

build foo.t: phony tests/foo_bar.t

default libs/libfoo.a

build tests: phony tests/foo_bar.t

''')

    def test_target_no_objects_one_executable(self):
        t = MockTarget('m_foo',
                       [Source('executable',
                               'm_foo',
                               'foo/foo_bar.m.cpp libs/libfoo.a',
                               'cxx',
                               ' -Ibam',
                               'apps/m_foo')],
                       [],
                       [],
                       [],
                       'apps/m_foo')
        result = io.StringIO()
        generate([t], {
            'cc':  '1',
            'c++': '2',
            'ar':  '3',
        }, result)
        assert(result.getvalue() == boilerplate + u'''\
build apps/m_foo: cxx-executable foo/foo_bar.m.cpp libs/libfoo.a
  flags = -Ibam

build m_foo: phony apps/m_foo

default apps/m_foo

''')

    def test_ld_input_generates_phony(self):
        t = MockTarget('m_foo', [], [], [], ['foo'], None)
        result = io.StringIO()
        generate([t], {
            'cc':  '1',
            'c++': '2',
            'ar':  '3',
        }, result)
        assert(result.getvalue() == boilerplate + u'''\
build foo: phony {}

'''.format(os.devnull))
