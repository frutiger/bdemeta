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

def get_items(items_file):
    items = []
    for l in items_file:
        if len(l) > 1 and l[0] != '#':
            items = items + l.split()
    return items

def group_members(group):
    packages_filename = os.path.join( resolve_group(group),
                                     'group',
                                      group + '.mem')
    with open(packages_filename) as packages_file:
        return get_items(packages_file)

def package_members(group, package):
    components_filename = os.path.join( resolve_group(group),
                                        package,
                                       'package',
                                        package + '.mem')
    with open(components_filename) as components_file:
        return get_items(components_file)

def group_dependencies(group):
    dependencies_filename = os.path.join( resolve_group(group),
                                         'group',
                                          group + '.dep')
    with open(dependencies_filename) as dependencies_file:
        items = set(get_items(dependencies_file))

    if len(items) == 0:
        return items
    else:
        return items | reduce(\
                lambda x, y: x | y,
                [group_dependencies(i) for i in items])

def package_dependencies(group, package):
    dependencies_filename = os.path.join( resolve_group(group),
                                          package,
                                         'package',
                                          package + '.dep')
    with open(dependencies_filename) as dependencies_file:
        items = set(get_items(dependencies_file))

    if len(items) == 0:
        return items
    else:
        return items | reduce(\
                lambda x, y: x | y,
                [package_dependencies(group, i) for i in items])

def package_path(group, package):
    return os.path.join(resolve_group(group), package)

def traverse(node, deps):
    return {node} | reduce(set.union,
                           [traverse(n, deps) for n in deps(node)],
                           set())

def tsort(top_nodes, dependencies):
    tsorted = []
    nodes = reduce(set.union,
                   [traverse(node, dependencies) for node in top_nodes])
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
        for p in tsort({package},
                       lambda p: package_dependencies(group, p)):
            includes.append(package_path(group, p))

        for c in package_members(group, package):
            path = os.path.join(resolve_group(group), package)
            components[c] = {
                'includes': includes,
                'cpp':      os.path.join(path, c + '.cpp'),
                'object':   os.path.join('out', 'objs', c + '.o'),
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
    print('-Lout/libs {}'.format(' '.join(['-l' + dep for dep in deps])))

def makefile(args):
    lib_rule = '''\
{lib}: {objects} | out/libs
	ar -crs {lib} {objects}
'''
    object_rule = '''\
{object}: {cpp} {headers} | out/objs
	$(CXX) -c {includes} {cpp} -o {object}
'''
    out_dir_rules = '''\
out/libs:
	mkdir -p out/libs

out/objs:
	mkdir -p out/objs
'''

    lib     = os.path.join('out', 'libs', 'lib{}.a'.format(args.group))

    cs      = components(args.group)
    objects = ' '.join(c['object'] for c in cs.values())

    print(lib_rule.format(lib = lib, objects = objects))
    for c in sorted(cs.keys()):
        incls    = cs[c]['includes']
        headers  = ' '.join([os.path.join(path, '*') for path in incls])
        includes = ' '.join(['-I' + path             for path in incls])
        print(object_rule.format(object   = cs[c]['object'],
                                 cpp      = cs[c]['cpp'],
                                 headers  = headers,
                                 includes = includes))
    print(out_dir_rules)

def ninja(args):
    rules = '''\
rule cc
  deps    = gcc
  depfile = $out.d
  command = c++ $cflags -c $in -MMD -MF $out.d -o $out

rule ar
  command = ar -crs $out $in
'''
    lib_template='''\
build {lib}: ar {objects}
'''
    object_template='''\
build {object}: cc {cpp}
  cflags = -Dunix {includes}
'''

    deps    = tsort({ args.group }, group_dependencies)
    libs    = ['-l' + dep for dep in deps]
    lib     = os.path.join('out', 'libs', 'lib{}.a'.format(args.group))

    cs      = components(args.group)
    objects = ' '.join(c['object'] for c in cs.values())

    print(rules)
    print(lib_template.format(lib = lib, objects = objects))
    for c in sorted(cs.keys()):
        includes = ' '.join(['-I' + path for path in cs[c]['includes']])
        print(object_template.format(object   = cs[c]['object'],
                                     cpp      = cs[c]['cpp'],
                                     includes = includes))

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

