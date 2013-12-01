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

def main():
    parser = argparse.ArgumentParser();
    parser.add_argument('action', choices={'cflags', 'mkmk'})
    parser.add_argument('group', type=str)
    args = parser.parse_args()

    group = args.group
    if args.action == 'cflags':
        paths = []
        for g in set([group]) | group_dependencies(group):
            for p in group_members(g):
                paths.append(package_path(g, p))
        print(' '.join(['-I' + path for path in paths]))
    elif args.action == 'mkmk':
        components = {}
        for package in group_members(group):
            paths = []
            for g in group_dependencies(group):
                for p in group_members(g):
                    paths.append(package_path(g, p))
            for p in set([package]) | package_dependencies(group, package):
                paths.append(package_path(group, p))

            for c in package_members(group, package):
                components[c] = {
                    'cpp': os.path.join(resolve_group(group), package, c + '.cpp'),
                    'object': os.path.join('out', 'objs', c + '.o'),
                    'includes': ' '.join(['-I' + path for path in paths]),
                }

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

        print('''out/libs:
	mkdir -p out/libs
''')

        print('''out/objs:
	mkdir -p out/objs
''')

if __name__ == '__main__':
    main()

