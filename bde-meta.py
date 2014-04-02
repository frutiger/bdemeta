#!/usr/bin/env python

from __future__ import print_function
from functools  import reduce

import argparse
import collections
import copy
import glob
import io
import itertools
import multiprocessing
import os
import subprocess
import sys

def memoize(function):
    results = {}
    def inner(*args):
        if args in results:
            result = results[args]
        else:
            result = function(*args)
            results[args] = result
        return copy.copy(result)
    return inner

@memoize
def traverse(ns):
    return reduce(frozenset.union,
                  (traverse(n.dependencies()) for n in ns),
                  ns)

@memoize
def tsort(nodes):
    tsorted = []
    marks   = {}

    def visit(node):
        if node.name not in marks:
            marks[node.name] = 'working'
            for child in node.dependencies():
                visit(child)
            marks[node.name] = 'done'
            tsorted.insert(0, node)
        elif marks[node.name] == 'done':
            return
        else:
            raise RuntimeError('cyclic graph')

    map(visit, nodes)
    return tsorted

@memoize
def bde_items(*args):
    items_filename = os.path.join(*args)
    items = []
    with open(items_filename) as items_file:
        for l in items_file:
            if len(l) > 1 and l[0] != '#':
                items = items + l.split()
    return frozenset(items)

class Unit(object):
    def __init__(self, name, defs):
        self.name   = name
        self._defs  = defs

    def __eq__(self, other):
        return self.name == other.name

    def __cmp__(self, other):
        return cmp(self.name, other.name)

    def __hash__(self):
        return hash(self.name)

    def dependencies(self):
        return frozenset()

    def defs(self, linker_flags=True):
        if linker_flags:
            return self._defs
        else:
            return filter(lambda x: x[:2] != '-L' and \
                                    x[:2] != '-l', self._defs)

class Group(Unit):
    def __init__(self, path, defs, resolver):
        super(Group, self).__init__(os.path.basename(path), defs)
        self.path     = path
        self.resolver = resolver

    def _packages(self, package=None):
        class Package(object):
            def __init__(self, *args):
                self.path = os.path.realpath(os.path.join(*args))
                self.name = os.path.basename(self.path)

            def __eq__(self, other):
                return self.name == other.name

            def __cmp__(self, other):
                return cmp(self.name, other.name)

            def __hash__(self):
                return hash(self.name)

            @memoize
            def dependencies(self):
                names = bde_items(self.path, 'package', self.name + '.dep')
                return frozenset(Package(self.path,
                                         os.path.pardir,
                                         name) for name in names)

            def defs(self):
                return '-I{}'.format(self.path)

            def components(self):
                if '+' in self.name:
                    # A '+' in a package name means all of its contents should
                    # be put into the archive
                    return filter(os.path.isfile, os.listdir(self.path))
                else:
                    return bde_items(self.path, 'package', self.name + '.mem')

        if package is None:
            names = bde_items(self.path, 'group', self.name + '.mem')
            return tsort(frozenset(Package(self.path, n) for n in names))
        else:
            return tsort(traverse(frozenset((Package(self.path,
                                                     package.name),))))

    @memoize
    def dependencies(self):
        names = bde_items(self.path, 'group', self.name + '.dep')
        return frozenset(self.resolver(name) for name in names)

    def defs(self, linker_flags=True):
        result = [p.defs() for p in self._packages()]
        if linker_flags:
            result.append('-Lout/libs')
            result.append('-l' + self.name)
        result.extend(self._defs)
        return result

    def components(self):
        deps = tsort(traverse(frozenset((self,))))
        deps.remove(self)
        deps_cflags  = reduce(list.__add__, [d.defs(False) for d in deps], [])
        deps_ldflags = reduce(list.__add__, [d.defs()      for d in deps], [])

        result = {}
        for package in self._packages():
            package_defs = [p.defs() for p in self._packages(package)]
            cflags       = deps_cflags  + package_defs + self.defs(False)
            ldflags      = deps_ldflags                + self.defs()
            for c in package.components():
                result[c] = {
                    'cflags':  cflags,
                    'ldflags': ldflags,
                    'path':    package.path,
                }
        return result

def get_resolver(roots, defs):
    def resolve(name):
        for root in roots:
            candidate = os.path.join(root.strip(), 'groups', name)
            if os.path.isdir(candidate):
                return Group(candidate, defs[name], resolve)
        return Unit(name, defs[name])
    return resolve

def walk(units):
    return ' '.join(u.name for u in tsort(traverse(units)))

def flags(units):
    units  = tsort(traverse(units))
    flags  = reduce(list.__add__, [u.defs() for u in units])
    return ' '.join(flags)

def ninja(units, file):
    rules = u'''\
rule cc-object
  deps    = gcc
  depfile = $out.d
  command = c++ -c $flags $in -MMD -MF $out.d -o $out

rule cc-test
  deps    = gcc
  depfile = $out.d
  command = c++ $flags $in -MMD -MF $out.d -o $out

rule ar
  command = ar -crs $out $in

'''
    lib_template=u'''\
build {lib}: ar {objects} | {libs}

default {lib}

'''
    tests_template=u'''\
build tests: phony {tests}

'''
    obj_template=u'''\
build {object}: cc-object {cpp}
  flags = {flags}

'''
    test_template=u'''\
build {test}: cc-test {driver}
  flags = {flags}

'''

    join  = lambda l: ' '.join(l)
    pjoin = os.path.join
    obj   = lambda c: pjoin('out', 'objs',  c + '.o')
    test  = lambda c: pjoin('out', 'tests', c + '.t')
    lib   = lambda l: pjoin('out', 'libs', 'lib{}.a'.format(l.name))

    file.write(rules)

    units = tsort(traverse(units))

    all_tests = []
    for unit in units:
        if not isinstance(unit, Group):
            continue

        components = unit.components()
        objects    = join((obj(c)  for c in components.keys()))
        tests      = join((test(c) for c in components.keys()))
        all_tests.append(tests)

        dep_units = filter(lambda x: isinstance(x, Group),
                           tsort(traverse(frozenset((unit,)))))
        dep_units.remove(unit)

        file.write(lib_template.format(lib     = lib(unit),
                                       objects = objects,
                                       libs    = join(map(lib, dep_units))))

        for name in sorted(components.keys()):
            c          = components[name]
            obj_flags  = ' '.join(c['cflags'])
            test_flags = ' '.join(c['cflags'] + c['ldflags'])
            file.write(obj_template.format(
                                   object = obj(name),
                                   cpp    = pjoin(c['path'], name + '.cpp'),
                                   flags  = obj_flags))
            file.write(test_template.format(
                                   test   = test(name),
                                   driver = pjoin(c['path'], name + '.t.cpp'),
                                   flags  = test_flags))

    file.write(tests_template.format(tests = join(all_tests)))

def runtest(test):
    for case in itertools.count():
        rc = subprocess.call((test, str(case)))
        if rc == 0:
            continue
        elif rc == 255:
            break
        else:
            raise RuntimeError('{test} case {case} failed'.format(test = test,
                                                                  case = case))

def runtests(tests):
    if len(tests) == 0:
        tests = glob.glob(os.path.join('out', 'tests', '*'))
    else:
        tests = [os.path.join('out', 'tests', t + '.t') for t in tests]

    multiprocessing.Pool().map(runtest, sorted(tests))

def parse_args(args):
    class NullAction(argparse.Action):
        def __call__(self, parser, namespace, values, option_string):
            pass

    parser = argparse.ArgumentParser(description='build and test BDE-style '
                                                 'code');
    parser.add_argument('--root',
                         action='append',
                         metavar='ROOT',
                         dest='roots',
                         help='Add the specified ROOT to the package '
                              'group search path')

    # This is added purely for help display purposes.  Hence, we use the
    # 'NullAction' to drop any arguments that might match this
    parser.add_argument('--<name>.def',
                         action=NullAction,
                         metavar='DEF',
                         help='Append the specified DEF when generating flags '
                              'for the dependency with the specified <name>.')

    subparser = parser.add_subparsers(metavar='MODE')

    walk_parser = subparser.add_parser('walk',
                                        help='Walk and topologically sort '
                                             'dependencies',
                                        description='Print the list of '
                                                    'dependencies of the '
                                                    'specified GROUPs in '
                                                    'topologically sorted '
                                                    'order')
    walk_parser.add_argument('groups', nargs='+', metavar='GROUP')
    walk_parser.set_defaults(mode='walk')

    flags_parser = subparser.add_parser('flags',
                                         help='Produce flags for building '
                                              'dependents',
                                         description='Produce flags that '
                                                     'will allow a '
                                                     'compilation unit '
                                                     'depending on the '
                                                     'specified GROUPs to '
                                                     'compile correctly')
    flags_parser.add_argument('groups', nargs='+', metavar='GROUP')
    flags_parser.set_defaults(mode='flags')

    ninja_parser = subparser.add_parser('ninja',
                                         help='Generate a ninja build file',
                                         description='Generate a ninja build '
                                                     'file that will build '
                                                     'statically linked '
                                                     'libraries and tests for '
                                                     'the specified GROUPs '
                                                     'and all dependent '
                                                     'groups')
    ninja_parser.add_argument('groups', nargs='+', metavar='GROUP')
    ninja_parser.set_defaults(mode='ninja')

    runtests_parser = subparser.add_parser('runtests',
                                            help='Run BDE-style unit tests',
                                            description='Run all of the '
                                                        'optionally specified '
                                                        'BDE-style TESTs '
                                                        'found in '
                                                        '\'out/tests\'; if '
                                                        'none are specified, '
                                                        'then run all the '
                                                        'tests in that '
                                                        'directory')
    runtests_parser.add_argument('tests', nargs='*', metavar='TEST')
    runtests_parser.set_defaults(mode='runtests')

    if os.path.isfile(os.path.expanduser('~/.bdemetarc')):
        with open(os.path.expanduser('~/.bdemetarc')) as f:
            args = f.read().split() + args

    args, unmatched = parser.parse_known_args(args=args)

    args.user_defs = collections.defaultdict(list)

    index = 0
    while index < len(unmatched):
        item = unmatched[index]
        if '=' in item:
            key   = item[:item.find('=')]
            value = item[item.find('=') + 1:]
        else:
            key = item
            if index + 1 == len(unmatched):
                raise RuntimeError('no matching value for {}'.format(key))
            index = index + 1
            value = unmatched[index]
        index = index + 1

        key = key.split('.')
        if len(key) != 2:
            raise RuntimeError('flag should be <unit>.def')

        if key[1] != 'def':
            raise RuntimeError(('flag should be {0}.def').format(key[0]))

        args.user_defs[key[0][2:]].append(value)

    return args

def main(args):
    args     = parse_args(args)
    resolver = get_resolver(args.roots, args.user_defs)

    if hasattr(args, 'groups'):
        groups = frozenset(resolver(unit) for unit in args.groups)

    if   args.mode == 'walk':
        print(walk(groups))
    elif args.mode == 'flags':
        print(flags(groups))
    elif args.mode == 'ninja':
        ninja(groups, sys.stdout)
    elif args.mode == 'runtests':
        runtests(args.tests)
    else:
        return -1

if __name__ == '__main__':
    try:
        sys.exit(main(sys.argv[1:]))
    except RuntimeError as e:
        print(e, file=sys.stderr)
        sys.exit(-1)

