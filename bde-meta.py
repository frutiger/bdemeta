#!/usr/bin/env python

from __future__  import print_function
from functools   import reduce
from collections import defaultdict

import argparse
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
        if node.name() not in marks:
            marks[node.name()] = 'working'
            for child in node.dependencies():
                visit(child)
            marks[node.name()] = 'done'
            tsorted.insert(0, node)
        elif marks[node.name()] == 'done':
            return
        else:
            raise RuntimeError('cyclic graph')

    [visit(n) for n in nodes]
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
    def __init__(self, resolver, name, dependencies, flags):
        self._resolver     = resolver
        self._name         = name
        self._dependencies = dependencies
        self._flags        = flags

    def __eq__(self, other):
        return self._name == other._name

    def __cmp__(self, other):
        return cmp(self._name, other._name)

    def __hash__(self):
        return hash(self._name)

    def name(self):
        return self._name

    @memoize
    def dependencies(self):
        return frozenset(self._resolver(name) for name in self._dependencies)

    def flags(self, type):
        return self._flags[type]

class Group(Unit):
    def __init__(self, resolver, path, dependencies, flags):
        self._path   = path
        name         = os.path.basename(path)
        dependencies = frozenset(dependencies)
        super(Group, self).__init__(
                        resolver,
                        name,
                        dependencies | bde_items(path, 'group', name + '.dep'),
                        flags)

    def _packages(self, package=None):
        class Package(object):
            def __init__(self, *args):
                self._path = os.path.realpath(os.path.join(*args))
                self._name = os.path.basename(self._path)

            def __eq__(self, other):
                return self._name == other._name

            def __cmp__(self, other):
                return cmp(self._name, other._name)

            def __hash__(self):
                return hash(self._name)

            def path(self):
                return self._path

            def name(self):
                return self._name

            @memoize
            def dependencies(self):
                names = bde_items(self._path, 'package', self._name + '.dep')
                return frozenset(Package(self._path,
                                         os.path.pardir,
                                         name) for name in names)

            def flags(self):
                return '-I{}'.format(self._path)

            def components(self):
                if '+' in self._name:
                    # A '+' in a package name means all of its contents should
                    # be put into the archive
                    return filter(os.path.isfile,
                                  map(lambda x: os.path.join(self.path(), x),
                                      os.listdir(self.path())))
                else:
                    return bde_items(self._path,
                                    'package',
                                     self._name + '.mem')

        if package is None:
            names = bde_items(self._path, 'group', self._name + '.mem')
            return tsort(frozenset(Package(self._path, n) for n in names))
        else:
            return tsort(traverse(frozenset((Package(self._path,
                                                     package._name),))))

    def flags(self, type):
        if type == 'c':
            return [p.flags() for p in self._packages()] + self._flags['c']
        elif type == 'ld':
            return ['-Lout/libs', '-l' + self._name]     + self._flags['ld']
        else:
            raise RuntimeError('Unknown flag type: ' + type)

    def components(self):
        deps = tsort(traverse(frozenset((self,))))
        deps.remove(self)
        deps_cflags  = reduce(list.__add__, [d.flags('c')  for d in deps], [])
        deps_ldflags = reduce(list.__add__, [d.flags('ld') for d in deps], [])

        result = {}
        for package in self._packages():
            package_flags = [p.flags() for p in self._packages(package)]
            cflags       = deps_cflags  + package_flags + self.flags('c')
            ldflags      = deps_ldflags                 + self.flags('ld')

            if '+' in package.name():
                for c in package.components():
                    name, ext = os.path.splitext(c)
                    if ext == '.c' or ext == '.cpp':
                        result[c] = {
                            'cflags': cflags,
                            'source': os.path.join(package.path(), c),
                            'object': name + '.o',
                        }
            else:
                for c in package.components():
                    result[c] = {
                        'cflags':  cflags,
                        'ldflags': ldflags,
                        'source':  os.path.join(package.path(), c + '.cpp'),
                        'object':  c + '.o',
                        'driver':  os.path.join(package.path(), c + '.t.cpp'),
                        'test':    c + '.t',
                    }
        return result

def get_resolver(roots, dependencies, flags):
    def resolve(name):
        for root in roots:
            candidate = os.path.join(root.strip(), 'groups', name)
            if os.path.isdir(candidate):
                return Group(resolve,
                             candidate,
                             dependencies[name],
                             flags[name])
        return Unit(resolve, name, dependencies[name], flags[name])
    return resolve

def walk(units):
    return ' '.join(u.name() for u in tsort(traverse(units)))

def flags(units, type):
    units  = tsort(traverse(units))
    flags  = reduce(list.__add__, [u.flags(type) for u in units])
    return ' '.join(flags)

def ninja(units, cxx, ar, file):
    rules = u'''\
rule cc-object
  deps    = gcc
  depfile = $out.d
  command = {cxx} -c $flags $in -MMD -MF $out.d -o $out

rule cc-test
  deps    = gcc
  depfile = $out.d
  command = {cxx} $in $flags -MMD -MF $out.d -o $out

rule ar
  command = {ar} -crs $out $in

'''.format(cxx=cxx, ar=ar)
    lib_template=u'''\
build {lib}: ar {objects} | {libs}

default {lib}

'''
    tests_template=u'''\
build tests: phony {tests}

'''
    obj_template=u'''\
build {object}: cc-object {source}
  flags = {flags}

'''
    test_template=u'''\
build {test}: cc-test {driver} | {libs}
  flags = {flags}

'''

    join  = lambda l: ' '.join(l)
    pjoin = os.path.join
    obj   = lambda c: pjoin('out', 'objs',  c)
    test  = lambda c: pjoin('out', 'tests', c)
    lib   = lambda l: pjoin('out', 'libs', 'lib{}.a'.format(l.name()))

    file.write(rules)

    units = tsort(traverse(units))

    all_tests = []
    for unit in units:
        if not isinstance(unit, Group):
            continue

        components = unit.components()
        objects    = join((obj(c['object']) for c in components.values()))
        tests      = join((test(c['test'])  for c in components.values() \
                                                               if 'test' in c))
        all_tests.append(tests)

        units     = list(filter(lambda x: isinstance(x, Group),
                                tsort(traverse(frozenset((unit,))))))
        dep_units = list(filter(lambda x: x != unit, units))

        file.write(lib_template.format(lib     = lib(unit),
                                       objects = objects,
                                       libs    = join(map(lib, dep_units))))

        for name in sorted(components.keys()):
            c      = components[name]
            flags  = ' '.join(c['cflags'])
            file.write(obj_template.format(
                                   object = obj(c['object']),
                                   source = c['source'],
                                   flags  = flags))
            if 'driver' in c:
                flags = ' '.join(c['cflags'] + c['ldflags'])
                file.write(test_template.format(
                                               test   = test(c['test']),
                                               driver = c['driver'],
                                               flags  = flags,
                                               libs   = join(map(lib, units))))

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

def get_parser():
    parser = argparse.ArgumentParser(description='build and test BDE-style '
                                                 'code');
    parser.add_argument('--root',
                         action='append',
                         metavar='ROOT',
                         dest='roots',
                         default=[],
                         help='Add the specified ROOT to the package '
                              'group search path')

    parser.add_argument('--dependency',
                         action='append',
                         metavar='NAME:DEPENDENCY',
                         dest='dependencies',
                         default=[],
                         help='Consider the specified NAME to have the '
                              'specified DEPENDENCY.')

    parser.add_argument('--cflag',
                         action='append',
                         metavar='NAME:FLAG',
                         dest='cflags',
                         default=[],
                         help='Append the specified FLAG when generating '
                              'cflags for the dependency with the specified '
                              'NAME.')

    parser.add_argument('--ldflag',
                         action='append',
                         metavar='NAME:FLAG',
                         dest='ldflags',
                         default=[],
                         help='Append the specified FLAG when generating '
                              'ldflags for the dependency with the specified '
                              'NAME.')

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

    cflags_parser = subparser.add_parser('cflags',
                                          help='Produce cflags for compiling '
                                               'dependents',
                                          description='Produce flags that '
                                                      'will allow a '
                                                      'compilation unit '
                                                      'depending on the '
                                                      'specified GROUPs to '
                                                      'compile correctly')
    cflags_parser.add_argument('groups', nargs='+', metavar='GROUP')
    cflags_parser.set_defaults(mode='cflags')

    ldflags_parser = subparser.add_parser('ldflags',
                                           help='Produce flags for linking '
                                                'dependents',
                                           description='Produce flags that '
                                                       'will allow a '
                                                       'compilation unit '
                                                       'depending on the '
                                                       'specified GROUPs to '
                                                       'link correctly')
    ldflags_parser.add_argument('groups', nargs='+', metavar='GROUP')
    ldflags_parser.set_defaults(mode='ldflags')

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
    ninja_parser.add_argument('--cxx',
                               default='c++',
                               help='Use the specified CXX as the compiler '
                                    'to build objects and linker to build '
                                    'tests')
    ninja_parser.add_argument('--ar',
                               default='ar',
                               help='Use the specified AR as the archiver '
                                    'to build static libraries')
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

    return parser

def parse_args(args):
    if os.path.isfile(os.path.expanduser('~/.bdemetarc')):
        with open(os.path.expanduser('~/.bdemetarc')) as f:
            args = f.read().split() + args

    args = get_parser().parse_args(args=args)

    def set_user_options(args, kind):
        result = defaultdict(list)
        for value in getattr(args, kind):
            if len(value.split(':')) < 2:
                raise RuntimeError('flag value should be NAME:{}'.format(
                                                                 kind.upper()))

            name, option = value.split(':')
            result[name].append(option)
        delattr(args,  kind)
        setattr(args, 'user_' + kind, result)

    set_user_options(args, 'dependencies')
    set_user_options(args, 'cflags')
    set_user_options(args, 'ldflags')

    setattr(args, 'user_flags', defaultdict(lambda: {'c': [], 'ld': []}))
    for unit in args.user_cflags:
        args.user_flags[unit]['c']  = args.user_cflags[unit]
    for unit in args.user_ldflags:
        args.user_flags[unit]['ld'] = args.user_ldflags[unit]
    delattr(args, 'user_cflags')
    delattr(args, 'user_ldflags')

    return args

def main(args):
    args     = parse_args(args)
    resolver = get_resolver(args.roots,
                            args.user_dependencies,
                            args.user_flags)

    if hasattr(args, 'groups'):
        groups = frozenset(resolver(unit) for unit in args.groups)

    if   args.mode == 'walk':
        print(walk(groups))
    elif args.mode == 'cflags':
        print(flags(groups, 'c'))
    elif args.mode == 'ldflags':
        print(flags(groups, 'ld'))
    elif args.mode == 'ninja':
        ninja(groups, args.cxx, args.ar, sys.stdout)
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

