#!/usr/bin/env python

from __future__ import print_function
from functools  import reduce

import argparse
import collections
import glob
import io
import itertools
import multiprocessing
import os
import subprocess
import sys

def traverse(ns):
    return reduce(set.union, (traverse(n.dependencies()) for n in ns), ns)

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

def bde_items(*args):
    items_filename = os.path.join(*args)
    items = []
    with open(items_filename) as items_file:
        for l in items_file:
            if len(l) > 1 and l[0] != '#':
                items = items + l.split()
    return set(items)

class Unit(object):
    def __init__(self, name, cflags, ldflags):
        self.name     = name
        self._cflags  = cflags
        self._ldflags = ldflags

    def __eq__(self, other):
        return self.name == other.name

    def __cmp__(self, other):
        return cmp(self.name, other.name)

    def __hash__(self):
        return hash(self.name)

    def __repr__(self):
        return 'Unit(\'{}\')'.format(self.name)

    def dependencies(self):
        return {}

    def cflags(self):
        return self._cflags

    def ldflags(self):
        return self._ldflags

class Group(Unit):
    def __init__(self, path, cflags, ldflags, resolver):
        super(Group, self).__init__(os.path.basename(path), cflags, ldflags)
        self.path     = path
        self.resolver = resolver

    def __repr__(self):
        return 'Group(\'{}\')'.format(self.name)

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

            def __repr__(self):
                return 'Package(\'{}\')'.format(self.name)

            def dependencies(self):
                names = bde_items(self.path, 'package', self.name + '.dep')
                return { Package(self.path,
                                 os.path.pardir,
                                 name) for name in names }

            def cflags(self):
                return '-I{}'.format(self.path)

            def components(self):
                return bde_items(self.path, 'package', self.name + '.mem')

        if package is None:
            names = bde_items(self.path, 'group', self.name + '.mem')
            return tsort({ Package(self.path, n) for n in names })
        else:
            return tsort(traverse({ Package(self.path, package.name) }))

    def dependencies(self):
        names = bde_items(self.path, 'group', self.name + '.dep')
        return { self.resolver(name) for name in names }

    def ldflags(self):
        return ['-l' + self.name] + self._ldflags

    def cflags(self):
        return [p.cflags() for p in self._packages()] + self._cflags

    def components(self):
        deps = tsort(traverse({ self }))
        deps.remove(self)
        deps_cflags = reduce(list.__add__, [d.cflags() for d in deps], [])

        result = {}
        for package in self._packages():
            package_cflags = [p.cflags() for p in self._packages(package)]
            cflags         = deps_cflags + package_cflags + self._cflags
            for c in package.components():
                result[c] = {
                    'cflags': cflags,
                    'path':   package.path,
                }
        return result

def get_resolver(roots, cflags, ldflags):
    def resolve(name):
        for root in roots:
            candidate = os.path.join(root.strip(), 'groups', name)
            if os.path.isdir(candidate):
                return Group(candidate, cflags[name], ldflags[name], resolve)
        return Unit(name, cflags[name], ldflags[name])
    return resolve

def deps(resolver, units):
    units = { resolver(unit) for unit in units }
    return ' '.join([u.name for u in tsort(traverse(units))])

def cflags(resolver, units):
    units    = { resolver(unit) for unit in units }
    units    = tsort(traverse(units))
    cflags = reduce(list.__add__, [u.cflags() for u in units])
    return ' '.join(cflags)

def ldflags(resolver, units):
    units   = { resolver(unit) for unit in units }
    units   = tsort(traverse(units))
    ldflags = reduce(list.__add__, [u.ldflags() for u in units])
    path    = os.path.join('out', 'libs')
    return '-L{path} {libs}'.format(path=path, libs=' '.join(ldflags))

def ninja(resolver, unit, file):
    rules = u'''\
rule cc-object
  deps    = gcc
  depfile = $out.d
  command = c++ $cflags -c $in -MMD -MF $out.d -o $out

rule cc-test
  deps    = gcc
  depfile = $out.d
  command = c++ $cflags $in $ldflags -MMD -MF $out.d -o $out

rule ar
  command = ar -crs $out $in
'''
    lib_template=u'''\
build {lib}: ar {objects}
default {lib}
'''
    tests_template=u'''\
build tests: phony {tests}
'''
    obj_template=u'''\
build {object}: cc-object {cpp}
  cflags = {cflags}
'''
    test_template=u'''\
build {test}: cc-test {driver}
  cflags  = {cflags}
  ldflags = {ldflags}
'''

    pjoin = os.path.join
    obj   = lambda c: pjoin('out', 'objs',  c + '.o')
    test  = lambda c: pjoin('out', 'tests', c + '.t')

    lib = pjoin('out', 'libs', 'lib{}.a'.format(unit))

    components = resolver(unit).components()
    objects    = ' '.join([obj(c)  for c in components.keys()])
    tests      = ' '.join([test(c) for c in components.keys()])

    file.write(rules)
    file.write(lib_template.format(lib = lib, objects = objects))
    file.write(tests_template.format(tests = tests))
    for name in sorted(components.keys()):
        c      = components[name]
        cflags = ' '.join(c['cflags'])
        file.write(obj_template.format(
                                    object   = obj(name),
                                    cpp      = pjoin(c['path'], name + '.cpp'),
                                    cflags   = cflags))
        file.write(test_template.format(
                                   test    = test(name),
                                   driver  = pjoin(c['path'], name + '.t.cpp'),
                                   cflags  = cflags,
                                   ldflags = ldflags(resolver, { unit })))

def runtest(test):
    for case in itertools.count():
        rc = subprocess.call([test, str(case)])
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

def main(args):
    parser = argparse.ArgumentParser();
    parser.add_argument('--root', action='append', dest='roots')

    subparser = parser.add_subparsers(title='subcommands')

    cflags_parser = subparser.add_parser('cflags', help='Generate a set of '
    '`-I` directives that will allow a compilation unit depending on the '
    'specified `<unit>`s to compile correctly.')
    cflags_parser.add_argument('units', nargs='+')
    cflags_parser.set_defaults(mode='cflags')

    deps_parser = subparser.add_parser('deps', help='Print the list of '
    'dependencies of the specified `<unit>`s in topologically sorted order.')
    deps_parser.add_argument('units', nargs='+')
    deps_parser.set_defaults(mode='deps')

    ldflags_parser = subparser.add_parser('ldflags', help='Generate a set of '
    '`-L` and `-l` directives that allow a link of objects depending on the '
    'specified `<unit>`s to link correctly.')
    ldflags_parser.add_argument('units', nargs='+')
    ldflags_parser.set_defaults(mode='ldflags')

    ninja_parser = subparser.add_parser('ninja', help='Generate a ninja '
    'build file that will build a statically linked library for the specified '
    '`<unit>`.')
    ninja_parser.add_argument('unit')
    ninja_parser.set_defaults(mode='ninja')

    runtests_parser = subparser.add_parser('runtests', help='Run all of the '
    'specified BDE-style `<test>` programs to be found in `out/tests` or all '
    'of the tests in that subdirectory.')
    runtests_parser.add_argument('tests', nargs='*')
    runtests_parser.set_defaults(mode='runtests')

    if os.path.isfile(os.path.expanduser('~/.bdemetarc')):
        with open(os.path.expanduser('~/.bdemetarc')) as f:
            args = f.read().split() + args

    args, unmatched = parser.parse_known_args(args=args)

    user_cflags  = collections.defaultdict(list)
    user_ldflags = collections.defaultdict(list)

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
            raise RuntimeError('flag should be <unit>.cflag or <unit>.ldflag')

        if   key[1] == 'cflag':
            user_cflags[key[0][2:]].append(value)
        elif key[1] == 'ldflag':
            user_ldflags[key[0][2:]].append(value)
        else:
            raise RuntimeError(('flag should be {0}.cflag or ' +
                                '{0}.ldflag').format(key[0]))

    resolver = get_resolver(args.roots, user_cflags, user_ldflags)
    if   args.mode == 'deps':
        return deps(   resolver, args.units)
    elif args.mode == 'cflags':
        return cflags( resolver, args.units)
    elif args.mode == 'ldflags':
        return ldflags(resolver, args.units)
    elif args.mode == 'ninja':
        return ninja( resolver,  args.unit, sys.stdout)
    elif args.mode == 'runtests':
        return runtests(args.tests)
    else:
        parser.print_help()
        return -1

if __name__ == '__main__':
    try:
        sys.exit(main(sys.argv[1:]))
    except RuntimeError as e:
        print(e, file=sys.stderr)
        sys.exit(-1)

