# bdemeta.resolver

import itertools
import os

import bdemeta.graph
import bdemeta.types

def bde_items(*args):
    items_filename = os.path.join(*args)
    items = []
    with open(items_filename) as items_file:
        for l in items_file:
            if len(l) > 0 and l[0] != '#':
                items = items + l.split()
    return items

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

class PackageResolver(object):
    def __init__(self, config, group_path):
        self._config     = config
        self._group_path = group_path

    def dependencies(self, name):
        return set(bde_items(self._group_path, name, 'package', name + '.dep'))

    def resolve(self, name, resolved_packages):
        path       = os.path.join(self._group_path, name)
        components = []
        if '+' in name:
            for file in os.listdir(path):
                root, ext = os.path.splitext(file)
                if ext != '.c' and ext != '.cpp':
                    continue
                components.append(bdemeta.types.Component(
                                          name + '_' + root,
                                          os.path.join(path, file),
                                          None))
        else:
            for item in bde_items(path, 'package', name + '.mem'):
                base   = os.path.join(path, item)
                source = base + '.cpp'
                driver = base + '.t.cpp'
                if not os.path.isfile(driver):
                    driver = None
                components.append(bdemeta.types.Component(item,
                                                          source,
                                                          driver))

        config = self._config['units'][name]
        deps   = lookup_dependencies(name,
                                     self.dependencies,
                                     resolved_packages)
        return bdemeta.types.Package(path,
                                     deps,
                                     config['internal_cflags'],
                                     config['external_cflags'],
                                     components)

class UnitResolver(object):
    def __init__(self, config):
        self._config = config

    def identify(self, name):
        if name[:2] == 'm_':
            for root in self._config['roots']:
                path = os.path.join(root.strip(), 'applications', name)
                if os.path.isdir(path):
                    return {
                        'type': 'application',
                        'path':  path,
                    }

        if len(name) == 3:
            for root in self._config['roots']:
                path = os.path.join(root.strip(), 'groups', name)
                if os.path.isdir(path):
                    return {
                        'type': 'group',
                        'path':  path,
                    }

        return {
            'type': None,
        }

    def dependencies(self, name):
        config = self._config['units'][name]

        if name == '#universal':
            return set()

        unit = self.identify(name)

        if unit['type'] == 'application':
            return set(itertools.chain(
                         config['deps'],
                         bde_items(unit['path'], 'application', name + '.dep'),
                         ['#universal']))

        if unit['type'] == 'group':
            return set(itertools.chain(
                               config['deps'],
                               bde_items(unit['path'], 'group', name + '.dep'),
                               ['#universal']))

        return set(config['deps'] + ['#universal'])

    def resolve(self, name, resolved_targets):
        config = self._config['units'][name]

        deps = lookup_dependencies(name,
                                   self.dependencies,
                                   resolved_targets)

        if name == '#universal':
            return bdemeta.types.Unit(name,
                                      deps,
                                      [],
                                      config['external_cflags'])

        unit = self.identify(name)

        if unit['type'] == 'application':
            return bdemeta.types.Application(unit['path'],
                                             deps,
                                             config['internal_cflags'],
                                             config['external_cflags'],
                                             config['ld_args'])

        if unit['type'] == 'group':
            packages = resolve(PackageResolver(self._config, unit['path']),
                               bde_items(unit['path'], 'group', name + '.mem'))
            return bdemeta.types.Group(unit['path'],
                                       deps,
                                       config['internal_cflags'],
                                       config['external_cflags'],
                                       packages,
                                       config['ld_args'])

        return bdemeta.types.Target(name,
                                    deps,
                                    config['internal_cflags'],
                                    config['external_cflags'],
                                    [],
                                    config['ld_args'],
                                    None)

