#!/usr/bin/env python

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

def get_packages(group):
    packages_filename = os.path.join( resolve_group(group),
                                     'group',
                                      group + '.mem')
    with open(packages_filename) as packages_file:
        return get_items(packages_file)

def get_components(group, package):
    components_filename = os.path.join( resolve_group(group),
                                        package,
                                       'package',
                                        package + '.mem')
    with open(components_filename) as components_file:
        return get_items(components_file)

def get_group_dependencies(group):
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
                [get_group_dependencies(i) for i in items])

def get_package_dependencies(group, package):
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
                [get_package_dependencies(group, i) for i in items])

def get_group_includes(groups):
    incs = []
    for g in groups:
        for p in get_packages(g):
            incs.append('-I' + os.path.join(resolve_group(g), p))
    return ' '.join(incs)

def get_package_includes(group, packages):
    incs = []
    for p in packages:
        incs.append('-I' + os.path.join(resolve_group(group), p))
    return ' '.join(incs)

def get_group_library(group):
    return os.path.join('out', 'libs', 'lib{}.a'.format(group))

def get_group_components(group):
    deps           = get_group_dependencies(group)
    group_includes = get_group_includes(deps)

    components = {}
    for p in get_packages(group):
        includes = group_includes + ' ' + get_package_includes(group,
                set([p]) | get_package_dependencies(group, p))
        cs = get_components(group, p)
        for c in cs:
            components[c] = {
                'cpp': os.path.join(resolve_group(group), p, c + '.cpp'),
                'object': os.path.join('out', 'objs', c + '.o'),
                'includes': includes,
            }
    return components

def print_group_targets(group):
    lib        = get_group_library(group)
    components = get_group_components(group)
    objects    = ' '.join(c['object'] for c in components.values())

    print('''{lib}: {objects} | out/libs
	ar -qs {lib} {objects}
'''.format(lib=lib, objects=objects))

    for c in components.values():
        print('''{obj}: {cpp} | out/objs
	$(CXX) -c $(CXXFLAGS) {includes} {cpp} -o {obj}
'''.format(obj=c['object'], cpp=c['cpp'], includes=c['includes']))

def main():
    parser = argparse.ArgumentParser();
    parser.add_argument('action', choices={'cflags', 'deps', 'mkmk'})
    parser.add_argument('group', type=str)
    args = parser.parse_args()

    group = args.group
    if args.action == 'cflags':
        print(get_group_includes(
            set([group]) | get_group_dependencies(group)))
    elif args.action == 'deps':
        print('\n'.join(list(get_group_dependencies(group))))
    elif args.action == 'mkmk':
        lib      = get_group_library(group)
        deps     = get_group_dependencies(group)
        dep_libs = (get_group_library(g) for g in deps)

        components = get_group_components(group)
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

if __name__ == '__main__':
    main()

