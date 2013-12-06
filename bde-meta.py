#!/usr/bin/env python2

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

def tsort(name, dependencies):
    tsorted = []
    nodes   = {}

    def visit(node):
        if node['mark'] == 'temporary':
            raise RuntimeError('cyclic graph')
        if node['mark'] == 'none':
            node['mark'] = 'temporary'
            for child in dependencies(node['name']):
                if child not in nodes:
                    nodes[child] = {'mark': 'none', 'name': child}
                visit(nodes[child])
            node['mark'] = 'permanent'
            tsorted.insert(0, node['name'])
    visit({'mark': 'none', 'name': name})

    return tsorted

def group_library(group):
    return os.path.join('out', 'libs', 'lib{}.a'.format(group))

def group_components(group):
    components = {}
    for package in group_members(group):
        paths = []
        for g in tsort(group, group_dependencies)[1:]:
            for p in group_members(g):
                paths.append(package_path(g, p))
        for p in tsort(package, lambda p: package_dependencies(group, p)):
            paths.append(package_path(group, p))

        for c in package_members(group, package):
            components[c] = {
                'cpp': os.path.join(resolve_group(group), package, c + '.cpp'),
                'object': os.path.join('out', 'objs', c + '.o'),
                'includes': ' '.join(['-I' + path for path in paths]),
            }
    return components

def print_group_targets(group):
    lib        = group_library(group)
    components = group_components(group)
    objects    = ' '.join(c['object'] for c in components.values())

    print('''{lib}: {objects} | out/libs
	ar -qs {lib} {objects}
'''.format(lib=os.path.join('out', 'libs', 'lib{}.a'.format(group)),
           objects=' '.join(c['object'] for c in components.values())))

    for component in components.values():
        print('''{obj}: | out/objs
	$(CXX) -c {includes} {cpp} -o {obj}
'''.format(obj=component['object'],
           cpp=component['cpp'],
           includes=component['includes']))

def main():
    parser = argparse.ArgumentParser();
    parser.add_argument('action', choices={'cflags', 'mkmk', 'deps'})
    parser.add_argument('group', type=str)
    args = parser.parse_args()

    group = args.group
    if args.action == 'cflags':
        paths = []
        deps  = tsort(group, group_dependencies)
        for g in tsort(group, group_dependencies):
            for p in group_members(g):
                paths.append(package_path(g, p))
        print(' '.join(['-I' + path for path in paths] +
                       ['-Lout/libs'] +
                       ['-l' + dep for dep in deps]))
    elif args.action == 'mkmk':
        lib      = group_library(group)
        deps     = get_group_dependencies(group)
        dep_libs = (group_library(g) for g in deps)

        components = group_components(group)
        objects = ' '.join(c['object'] for c in components.values())

        print('.PHONY: all deps\n')
        print('CXXFLAGS+=-Dunix\n')

        print_group_targets(group)

        print('all: {lib} deps\n'.format(lib=lib))

        print('deps: ' + ' '.join(list(dep_libs)) + '\n')

        for g in deps:
            print_group_targets(g)

        print('''out/libs:
	mkdir -p out/libs
''')

        print('''out/objs:
	mkdir -p out/objs
''')
    elif args.action == 'deps':
        print(' '.join(tsort(group, group_dependencies)))
    else:
        raise RuntimeError('Unknown action: ' + args.action)

if __name__ == '__main__':
    main()

