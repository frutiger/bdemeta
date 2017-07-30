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

def lookup_dependencies(name, get_dependencies, resolved_targets):
    targets = bdemeta.graph.tsort([name], get_dependencies, sorted)
    targets.remove(name)
    return [resolved_targets[t] for t in targets]

def resolve(resolver, names):
    store = {}
    targets = bdemeta.graph.tsort(names, resolver.dependencies, sorted)
    for t in reversed(targets):
        store[t] = resolver.resolve(t, store)
    return [store[t] for t in targets]

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

class TargetResolver(object):
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

        self._lazily_bound = set(config.get('lazily_bound', []))

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
            path = TargetResolver._is_group(root, name)
            if path:
                return {
                    'type': 'group',
                    'path':  path,
                }

            path = TargetResolver._is_standalone(root, name)
            if path:
                return {
                    'type': 'package',
                    'path':  path,
                }

            path = TargetResolver._is_cmake(root, name)
            if path:
                return {
                    'type': 'cmake',
                    'path':  path,
                }

            if name in self._virtuals:
                return {
                    'type': 'virtual',
                }

        raise TargetNotFoundError(name)

    def dependencies(self, name):
        target = self.identify(name)

        result = set()
        if name in self._virtuals:
            result.add(self._virtuals[name])
        if target['type'] == 'group' or target['type'] == 'package':
            result |= bde_items(target['path']/target['type']/(name + '.dep'))
        return result

    def resolve(self, name, resolved_targets):
        deps = lookup_dependencies(name,
                                   self.dependencies,
                                   resolved_targets)

        target = self.identify(name)

        if target['type'] == 'group':
            path = target['path']/'group'/(name + '.mem')
            packages = resolve(PackageResolver(target['path']),
                               bde_items(path))
            result = bdemeta.types.Group(target['path'], deps, packages)

        if target['type'] == 'package':
            components = build_components(target['path'])
            result = bdemeta.types.Package(target['path'], deps, components)

        if target['type'] == 'cmake':
            result = bdemeta.types.CMake(name, target['path'])

        if target['type'] == 'virtual':
            result = bdemeta.types.Target(name, deps)

        if name in self._providers:
            result.has_output = False

        if name in self._lazily_bound:
            result.lazily_bound = True

        return result

