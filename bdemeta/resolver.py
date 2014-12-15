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
            if len(l) > 1 and l[0] != '#':
                items = items + l.split()
    return items

class PackageResolver(object):
    def __init__(self, config, group_path):
        self._config      = config
        self._group_path  = group_path
        self._resolutions = {}

    def dependencies(self, name):
        return itertools.chain(self._config['units'][name]['deps'],
                               bde_items(self._group_path,
                                         name,
                                         'package',
                                         name + '.dep'))

    def _resolve(self, name):
        path   = os.path.join(self._group_path, name)
        config = self._config['units'][name]

        deps = bdemeta.graph.tsort([name], self.dependencies, sorted)
        deps = [self._cached_resolve(d) for d in deps if d != name]

        components = []
        if '+' in path:
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
        return bdemeta.types.Package(path,
                                     deps,
                                     config['internal_cflags'],
                                     config['external_cflags'],
                                     components)

    def _cached_resolve(self, name):
        if name not in self._resolutions:
            self._resolutions[name] = self._resolve(name)
        return self._resolutions[name]

    def __call__(self, names):
        units = bdemeta.graph.tsort(names, self.dependencies, sorted)
        return [self._cached_resolve(u) for u in units]

class Resolver(object):
    def __init__(self, config):
        self._config      = config
        self._resolutions = {}

    def _identify(self, name):
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
            return []

        unit = self._identify(name)

        if unit['type'] == 'application':
            return itertools.chain(
                         config['deps'],
                         bde_items(unit['path'], 'application', name + '.dep'),
                         ['#universal'])

        if unit['type'] == 'group':
            return itertools.chain(
                               config['deps'],
                               bde_items(unit['path'], 'group', name + '.dep'),
                               ['#universal'])

        return config['deps'] + ['#universal']

    def _resolve(self, name):
        config = self._config['units'][name]

        deps = bdemeta.graph.tsort([name], self.dependencies, sorted)
        deps = [self._cached_resolve(d) for d in deps if d != name]

        if name == '#universal':
            return bdemeta.types.Unit(name,
                                      deps,
                                      [],
                                      config['external_cflags'])

        unit = self._identify(name)

        if unit['type'] == 'application':
            return bdemeta.types.Application(unit['path'],
                                             deps,
                                             config['internal_cflags'],
                                             config['external_cflags'],
                                             config['ld_args'])

        if unit['type'] == 'group':
            package_resolver = PackageResolver(self._config, unit['path'])
            packages = package_resolver(bde_items(unit['path'],
                                                  'group',
                                                  name + '.mem'))
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

    def _cached_resolve(self, name):
        if name not in self._resolutions:
            self._resolutions[name] = self._resolve(name)
        return self._resolutions[name]

    def __call__(self, names):
        units = bdemeta.graph.tsort(names, self.dependencies, sorted)
        return [self._cached_resolve(u) for u in units]

