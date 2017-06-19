# bdemeta.resolver

import os

import bdemeta.graph
import bdemeta.types

class TargetNotFoundError(RuntimeError):
    pass

def bde_items(*args):
    items_filename = os.path.join(*args)
    items = []
    if os.path.isfile(items_filename):
        with open(items_filename) as items_file:
            for l in items_file:
                if len(l) > 0 and l[0] != '#':
                    items = items + l.split()
    return set(items)

def lookup_dependencies(name, get_dependencies, resolved_units):
    units = bdemeta.graph.tsort([name], get_dependencies, sorted)
    units.remove(name)
    return [resolved_units[u] for u in units]

def resolve(resolver, names):
    store = {}
    units = bdemeta.graph.tsort(names, resolver.dependencies, sorted)
    for u in reversed(units):
        store[u] = resolver.resolve(u, store)
    return [store[u] for u in units]

def build_components(path):
    name = os.path.basename(path)
    sources = []
    drivers = []
    if '+' in name:
        for file in os.listdir(path):
            root, ext = os.path.splitext(file)
            if ext != '.c' and ext != '.cpp':
                continue
            sources.append(os.path.join(path, file))
    else:
        for item in bde_items(path, 'package', name + '.mem'):
            base   = os.path.join(path, item)
            source = base + '.cpp'
            driver = base + '.t.cpp'
            if os.path.isfile(driver):
                drivers.append(driver)
            sources.append(source)
    return sources, drivers

class PackageResolver(object):
    def __init__(self, group_path):
        self._group_path = group_path

    def dependencies(self, name):
        return bde_items(self._group_path, name, 'package', name + '.dep')

    def resolve(self, name, resolved_packages):
        path             = os.path.join(self._group_path, name)
        sources, drivers = build_components(path)
        deps             = lookup_dependencies(name,
                                               self.dependencies,
                                               resolved_packages)
        return bdemeta.types.Package(path, deps, sources, drivers)

class UnitResolver(object):
    def __init__(self, config):
        self._roots = config['roots']

    def _is_group(root, name):
        path = os.path.join(root, 'groups', name)
        if os.path.isdir(path) and os.path.isdir(os.path.join(path, 'group')):
            return path

    def _is_standalone(root, name):
        for category in ['adapters']:
            path = os.path.join(root, category, name)
            if os.path.isdir(path) and \
                                  os.path.isdir(os.path.join(path, 'package')):
                return path

    def _is_cmake(root, name):
        path = os.path.join(root, 'thirdparty', name)
        if os.path.isdir(path) and \
                          os.path.isfile(os.path.join(path, 'CMakeLists.txt')):
            return path

    def identify(self, name):
        for root in self._roots:
            root = root.strip()
            path = UnitResolver._is_group(root, name)
            if path:
                return {
                    'type': 'group',
                    'path':  path,
                }

            path = UnitResolver._is_standalone(root, name)
            if path:
                return {
                    'type': 'package',
                    'path':  path,
                }

            path = UnitResolver._is_cmake(root, name)
            if path:
                return {
                    'type': 'cmake',
                    'path':  path,
                }

        raise TargetNotFoundError(name)

    def dependencies(self, name):
        unit = self.identify(name)

        result = set()
        if unit['type'] == 'group' or unit['type'] == 'package':
            result |= bde_items(unit['path'], unit['type'], name + '.dep')
        return result

    def resolve(self, name, resolved_targets):
        deps = lookup_dependencies(name,
                                   self.dependencies,
                                   resolved_targets)

        unit = self.identify(name)

        if unit['type'] == 'group':
            packages = resolve(PackageResolver(unit['path']),
                               bde_items(unit['path'], 'group', name + '.mem'))
            return bdemeta.types.Group(unit['path'], deps, packages)

        if unit['type'] == 'package':
            sources, drivers = build_components(unit['path'])
            return bdemeta.types.Package(unit['path'], deps, sources, drivers)

        if unit['type'] == 'cmake':
            return bdemeta.types.CMake(unit['path'])

        raise RuntimeError('Unknown unit: ' + unit)

