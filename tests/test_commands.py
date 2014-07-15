import io
from unittest import TestCase

from bdemeta.types    import Unit
from bdemeta.commands import walk, flags, ninja, runtests

boilerplate = u'''\
rule cc-object
  deps    = gcc
  depfile = $out.d
  command = 1 -c $flags $in -MMD -MF $out.d -o $out

rule cxx-object
  deps    = gcc
  depfile = $out.d
  command = 2 -c $flags $in -MMD -MF $out.d -o $out

rule cxx-test
  deps    = gcc
  depfile = $out.d
  command = 2 $in $flags -MMD -MF $out.d -o $out

rule ar
  command = 3 -crs $out $in

'''

class MockUnit(object):
    def __init__(self, name, dependencies, components):
        self._name         = name
        self._dependencies = dependencies
        self._components   = components

    def name(self):
        return self._name

    def dependencies(self):
        return self._dependencies

    def components(self):
        return self._components

    def result_type(self):
        return 'library'

class TestNinja(TestCase):
    def test_boilerplate(self):
        result = io.StringIO()
        ninja((), '1', '2', '3', result)
        assert(result.getvalue() == boilerplate)

    def test_component(self):
        u = MockUnit('foo', (), {
            'a': {
                'source': 'a.cpp',
                'object': 'a.o',
                'cflags': ['-Ia'],
            },
        })
        result = io.StringIO()
        ninja((u,), '1', '2', '3', result)
        assert(result.getvalue() == boilerplate + u'''\
build out/libs/libfoo.a: ar out/objs/a.o

build foo: phony out/libs/libfoo.a

default out/libs/libfoo.a

build out/objs/a.o: cxx-object a.cpp
  flags = -Ia

''')

    def test_component_with_dep(self):
        bar = MockUnit('bar', (), {
            'bar_1': {
                'source': 'bar_1.cpp',
                'object': 'bar_1.o',
                'cflags': [],
            },
        });
        foo = MockUnit('foo', (bar,), {
            'foo_1': {
                'source': 'foo_1.cpp',
                'object': 'foo_1.o',
                'cflags': [],
            },
        })
        result = io.StringIO()
        ninja((foo,), '1', '2', '3', result)
        assert(result.getvalue() == boilerplate + u'''\
build out/libs/libfoo.a: ar out/objs/foo_1.o | out/libs/libbar.a

build foo: phony out/libs/libfoo.a

default out/libs/libfoo.a

build out/objs/foo_1.o: cxx-object foo_1.cpp
  flags =

build out/libs/libbar.a: ar out/objs/bar_1.o

build bar: phony out/libs/libbar.a

default out/libs/libbar.a

build out/objs/bar_1.o: cxx-object bar_1.cpp
  flags =

''')

    def test_driver(self):
        u = MockUnit('foo', (), {
            'a': {
                'source':   'a.cpp',
                'object':   'a.o',
                'cflags':  ['-Ia'],
                'driver':   'a.t.cpp',
                'test':     'a.t',
                'ldflags': ['-lbar'],
            },
        })
        result = io.StringIO()
        ninja((u,), '1', '2', '3', result)
        assert(result.getvalue() == boilerplate + u'''\
build out/libs/libfoo.a: ar out/objs/a.o

build foo: phony out/libs/libfoo.a

default out/libs/libfoo.a

build out/objs/a.o: cxx-object a.cpp
  flags = -Ia

build out/tests/a.t: cxx-test a.t.cpp | out/libs/libfoo.a
  flags = -Ia -lbar

build a.t: phony out/tests/a.t

build tests: phony out/tests/a.t

''')
