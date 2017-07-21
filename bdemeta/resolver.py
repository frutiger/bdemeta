# bdemeta.resolver

import bdemeta.graph
import bdemeta.types

class TargetNotFoundError(RuntimeError):
    pass

def bde_items(path):
    items = []
    with path.open() as items_file:
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
    name = path.name
    components = []
    if '+' in name:
        for file in path.iterdir():
            if file.suffix == '.c' or file.suffix == '.cpp':
                components.append({
                    'header': None,
                    'source': file,
                    'driver': None,
                })
            elif file.suffix == '.h':
                components.append({
                    'header': file,
                    'source': None,
                    'driver': None,
                })
    else:
        for item in bde_items(path/'package'/(name + '.mem')):
            base   = path/item
            header = base.with_suffix('.h')
            source = base.with_suffix('.cpp')
            driver = base.with_suffix('.t.cpp')
            components.append({
                'header': header,
                'source': source,
                'driver': driver if driver.is_file() else None,
            })
    return components

class PackageResolver(object):
    def __init__(self, group_path):
        self._group_path = group_path

    def dependencies(self, name):
        return bde_items(self._group_path/name/'package'/(name + '.dep'))

    def resolve(self, name, resolved_packages):
        path       = self._group_path/name
        components = build_components(path)
        deps       = lookup_dependencies(name,
                                         self.dependencies,
                                         resolved_packages)
        return bdemeta.types.Package(path, deps, components)

class UnitResolver(object):
    def __init__(self, config):
        self._roots     = config['roots']
        self._virtuals  = {}
        self._providers = set()

        providers = config.get('providers', {})
        provideds  = set()
        for provider, all_provided in providers.items():
            provideds |= set(all_provided)
            for provided in all_provided:
                self._virtuals[provided] = provider

        self._providers = set(providers.keys()) - provideds

    def _is_group(root, name):
        path = root/'groups'/name
        if path.is_dir() and (path/'group').is_dir():
            return path

    def _is_standalone(root, name):
        for category in ['adapters']:
            path = root/category/name
            if path.is_dir() and (path/'package').is_dir():
                return path

    def _is_cmake(root, name):
        if root.stem == name and (root/'CMakeLists.txt').is_file():
            return root
        path = root/'thirdparty'/name
        if path.is_dir() and (path/'CMakeLists.txt').is_file():
            return path

    def identify(self, name):
        for root in self._roots:
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
                    'name':  name,
                    'path':  path,
                }

            if name in self._virtuals:
                return {
                    'type': 'virtual',
                    'name':  name,
                }

        raise TargetNotFoundError(name)

    def dependencies(self, name):
        unit = self.identify(name)

        result = set()
        if name in self._virtuals:
            result.add(self._virtuals[name])
        if unit['type'] == 'group' or unit['type'] == 'package':
            result |= bde_items(unit['path']/unit['type']/(name + '.dep'))
        return result

    def resolve(self, name, resolved_targets):
        deps = lookup_dependencies(name,
                                   self.dependencies,
                                   resolved_targets)

        unit = self.identify(name)

        if unit['type'] == 'group':
            packages = resolve(PackageResolver(unit['path']),
                               bde_items(unit['path']/'group'/(name + '.mem')))
            result = bdemeta.types.Group(unit['path'], deps, packages)

        if unit['type'] == 'package':
            components = build_components(unit['path'])
            result = bdemeta.types.Package(unit['path'], deps, components)

        if unit['type'] == 'cmake':
            result = bdemeta.types.CMake(name, unit['path'])

        if unit['type'] == 'virtual':
            result = bdemeta.types.Unit(name, deps)

        if name in self._providers:
            result.has_output = False
        return result

