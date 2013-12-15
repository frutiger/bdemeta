#!/usr/bin/env python

from __future__ import print_function
import argparse
import os

def resolve_group(group):
    for root in os.getenv('ROOTS').split(':'):
        candidate = os.path.join(root, 'groups', group)
        if os.path.isdir(candidate):
            return candidate
    raise RuntimeError('"' + group + '" not found in roots. Set the ROOTS ' +
                       'environment variable to a colon-separated set of ' +
                       'paths pointing to a set of BDE-style source roots.')

def package_path(group, package):
    return os.path.join(resolve_group(group), package)

def get_items(items_filename):
    items = []
    with open(items_filename) as items_file:
        for l in items_file:
            if len(l) > 1 and l[0] != '#':
                items = items + l.split()
    return set(items)

def group_members(group):
    return get_items(os.path.join( resolve_group(group),
                                  'group',
                                   group + '.mem'))

def package_members(group, package):
    return get_items(os.path.join( resolve_group(group),
                                   package,
                                  'package',
                                   package + '.mem'))

def group_dependencies(group):
    return get_items(os.path.join( resolve_group(group),
                                  'group',
                                   group + '.dep'))

def package_dependencies(group):
    return lambda package: get_items(os.path.join( resolve_group(group),
                                                   package,
                                                  'package',
                                                   package + '.dep'))

def traverse(nodes, deps):
    return reduce(set.union, [traverse(deps(n), deps) for n in nodes], nodes)

def tsort(top_nodes, dependencies):
    tsorted = []
    nodes = traverse(top_nodes, dependencies)
    nodes = {node: {'mark': 'none', 'name': node} for node in nodes}

    def visit(node):
        if node['mark'] == 'none':
            node['mark'] = 'temporary'
            for child in dependencies(node['name']):
                visit(nodes[child])
            node['mark'] = 'permanent'
            tsorted.insert(0, node['name'])
        elif node['mark'] == 'permanent':
            return
        else:
            raise RuntimeError('cyclic graph')

    map(visit, nodes.values())
    return tsorted

def components(group):
    components = {}
    for package in group_members(group):
        includes = []
        for g in tsort({group}, group_dependencies)[1:]:
            for p in group_members(g):
                includes.append(package_path(g, p))
        for p in tsort({package}, package_dependencies(group)):
            includes.append(package_path(group, p))

        for c in package_members(group, package):
            path = os.path.join(resolve_group(group), package)
            components[c] = {
                'includes': includes,
                'cpp':      os.path.join(path, c + '.cpp'),
                'object':   os.path.join('out', 'objs', c + '.o'),
                'drivers':  os.path.join(path, c + '.t.cpp'),
                'test':     os.path.join('out', 'tests', c + '.t'),
            }
    return components

def cflags(args):
    paths = []
    for g in tsort({args.group}, group_dependencies):
        for p in group_members(g):
            paths.append(package_path(g, p))
    print(' '.join(['-I' + path for path in paths]))

def deps(args):
    map(print, tsort(set(args.groups), group_dependencies))

def ldflags(args):
    deps = tsort(set(args.groups), group_dependencies)
    libs = ['-l' + dep for dep in deps]
    path = os.path.join('out', 'libs')

    print('-L{path} {libs}'.format(path=path, libs=' '.join(libs)))

def makefile(args):
    lib_rule = '''\
{lib}: {objects} | {libpath}
	ar -crs {lib} {objects}
'''
    object_rule = '''\
{object}: {cpp} {headers} | {objpath}
	$(CXX) -c {includes} {cpp} -o {object}
'''
    test_rule = '''\
{test}: {drivers} {headers} | {testpath}
	$(CXX) {includes} {drivers} {ldflags} -o {test}
'''
    out_dir_rules = '''\
{libpath}:
	mkdir -p {libpath}

{objpath}:
	mkdir -p {objpath}

{testpath}:
	mkdir -p {testpath}
'''

    libpath  = os.path.join('out', 'libs')
    objpath  = os.path.join('out', 'objs')
    testpath = os.path.join('out', 'tests')

    deps    = tsort({ args.group }, group_dependencies)
    libs    = ['-l' + dep for dep in deps]
    lib     = os.path.join(libpath, 'lib{}.a'.format(args.group))
    ldflags = '-L{libpath} {libs}'.format(libpath = libpath,
                                          libs    = ' '.join(libs))

    cs      = components(args.group)
    objects = ' '.join(c['object'] for c in cs.values())

    print(lib_rule.format(lib = lib, libpath = libpath, objects = objects))
    for c in sorted(cs.keys()):
        incls    = cs[c]['includes']
        headers  = ' '.join([os.path.join(path, '*') for path in incls])
        includes = ' '.join(['-I' + path             for path in incls])
        print(object_rule.format(object   = cs[c]['object'],
                                 objpath  = objpath,
                                 cpp      = cs[c]['cpp'],
                                 headers  = headers,
                                 includes = includes))
        print(test_rule.format(test     = cs[c]['test'],
                               testpath = testpath,
                               drivers  = cs[c]['drivers'],
                               headers  = headers,
                               includes = includes,
                               ldflags  = ldflags))
    print(out_dir_rules.format(libpath  = libpath,
                               objpath  = objpath,
                               testpath = testpath))

def ninja(args):
    rules = '''\
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
    lib_template='''\
build {lib}: ar {objects}
default {lib}
'''
    object_template='''\
build {object}: cc-object {cpp}
  cflags = -Dunix {includes}
'''
    test_template='''\
build {test}: cc-test {drivers}
  cflags  = -Dunix {includes}
  ldflags = {ldflags}
'''

    deps    = tsort({ args.group }, group_dependencies)
    libs    = ['-l' + dep for dep in deps]
    lib     = os.path.join('out', 'libs', 'lib{}.a'.format(args.group))
    ldflags = '-L{path} {libs}'.format(path = os.path.join('out', 'libs'),
                                       libs = ' '.join(libs))

    cs      = components(args.group)
    objects = ' '.join(c['object'] for c in cs.values())

    print(rules)
    print(lib_template.format(lib = lib, objects = objects))
    for c in sorted(cs.keys()):
        includes = ' '.join(['-I' + path for path in cs[c]['includes']])
        print(object_template.format(object   = cs[c]['object'],
                                     cpp      = cs[c]['cpp'],
                                     includes = includes))
        print(test_template.format(test     = cs[c]['test'],
                                   drivers  = cs[c]['drivers'],
                                   includes = includes,
                                   ldflags  = ldflags))

def main():
    parser    = argparse.ArgumentParser();
    subparser = parser.add_subparsers(title='subcommands')

    cflags_parser = subparser.add_parser('cflags', help='Generate a set of '
    '`-I` directives that will allow a compilation unit depending on the '
    'specified `<group>` to compile correctly.')
    cflags_parser.add_argument('group', type=str)
    cflags_parser.set_defaults(func=cflags)

    deps_parser = subparser.add_parser('deps', help='Print the list of '
    'dependencies of the specified `<group>`s in topologically sorted order.')
    deps_parser.add_argument('groups', type=str, nargs='+')
    deps_parser.set_defaults(func=deps)

    ldflags_parser = subparser.add_parser('ldflags', help='Generate a set of '
    '`-L` and `-l` directives that allow a link of objects depending on the '
    'specified `<group>`s to link correctly.')
    ldflags_parser.add_argument('groups', type=str, nargs='+')
    ldflags_parser.set_defaults(func=ldflags)

    makefile_parser = subparser.add_parser('makefile', help='Generate a '
    'makefile that will build a statically linked library for the specified '
    '`<group>`.')
    makefile_parser.add_argument('group', type=str)
    makefile_parser.set_defaults(func=makefile)

    ninja_parser = subparser.add_parser('ninja', help=' Generate a ninja '
    'build file that will build a statically linked library for the specified '
    '`<group>`.')
    ninja_parser.add_argument('group', type=str)
    ninja_parser.set_defaults(func=ninja)

    args = parser.parse_args()
    args.func(args)

if __name__ == '__main__':
    main()

