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

rule cxx-executable
  deps    = gcc
  depfile = $out.d
  command = 2 $cflags $in $ldflags -MMD -MF $out.d -o $out

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
        u = MockUnit('foo', (), ({
            'type':   'object',
            'input':  'a.cpp',
            'cflags': ' -Ia',
            'output': 'a.o',
        },))
        result = io.StringIO()
        ninja((u,), '1', '2', '3', result)
        assert(result.getvalue() == boilerplate + u'''\
build out/objs/a.o: cxx-object a.cpp
  flags = -Ia

build out/libs/libfoo.a: ar out/objs/a.o

build foo: phony out/libs/libfoo.a

default out/libs/libfoo.a

''')

    def test_component_with_dep(self):
        bar = MockUnit('bar', (), ({
            'type':   'object',
            'input':  'bar_1.cpp',
            'cflags': '',
            'output': 'bar_1.o',
        },))
        foo = MockUnit('foo', (bar,), ({
            'type':   'object',
            'input':  'foo_1.cpp',
            'cflags': '',
            'output': 'foo_1.o',
        },))
        result = io.StringIO()
        ninja((foo,), '1', '2', '3', result)
        assert(result.getvalue() == boilerplate + u'''\
build out/objs/foo_1.o: cxx-object foo_1.cpp
  flags =

build out/libs/libfoo.a: ar out/objs/foo_1.o | out/libs/libbar.a

build foo: phony out/libs/libfoo.a

build out/objs/bar_1.o: cxx-object bar_1.cpp
  flags =

build out/libs/libbar.a: ar out/objs/bar_1.o

build bar: phony out/libs/libbar.a

default out/libs/libfoo.a out/libs/libbar.a

''')

    def test_driver(self):
        u = MockUnit('foo', (), ({
            'type':    'test',
            'input':   'a.t.cpp',
            'cflags':  ' -Ia',
            'ldflags': ' -lbar',
            'output':  'a.t',
        },))
        result = io.StringIO()
        ninja((u,), '1', '2', '3', result)
        assert(result.getvalue() == boilerplate + u'''\
build out/tests/a.t: cxx-executable a.t.cpp | out/libs/libfoo.a
  cflags = -Ia
  ldflags = -lbar

build a.t: phony out/tests/a.t

build tests: phony out/tests/a.t

''')
