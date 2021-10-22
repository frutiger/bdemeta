# bdemeta.resolver

import abc
from pathlib import Path
from typing import (Callable, cast, Dict, Generic, List, Mapping, Optional,
                    Set, Sequence, TypeVar)
Node = TypeVar('Node')

import bdemeta.graph
from bdemeta.types import (Application, CMake, Config, Group, Identification,
                           Package, Pkg, Target)

class TargetNotFoundError(RuntimeError):
    pass

def bde_items(path: Path) -> Set[str]:
    items: List[str] = []
    with path.open() as items_file:
        for l in items_file:
            if len(l) > 0 and l[0] != '#':
                items = items + l.split()
    return set(items)

def lookup_dependencies(name: str,
                        deps: Callable[[str], Set[str]],
                        seen: Mapping[str, Node]) -> Sequence[Node]:
    targets = bdemeta.graph.tsort([name], deps, sorted)
    targets.remove(name)
    return [seen[t] for t in targets]

class Resolver(Generic[Node]):
    @abc.abstractmethod
    def resolve(self, name: str, resolved_nodes: Dict[str, Node]) -> Node:
        '''Resolve a target with the specified 'name' which has its
        dependencies already resolved and accessible by name in the specified
        'resolved_nodes'.'''

    @abc.abstractmethod
    def dependencies(self, name:str) -> Set[str]:
        '''Return the set of dependency names for a target with the specified
        'name'.'''

def resolve(resolver: Resolver[Node], names: List[str]) -> List[Node]:
    store: Dict[str, Node] = {}
    targets = bdemeta.graph.tsort(names, resolver.dependencies, sorted)
    for t in reversed(targets):
        store[t] = resolver.resolve(t, store)
    return [store[t] for t in targets]

def build_components(path: Path) -> List[Dict[str, Optional[str]]]:
    name = path.name
    components = []
    if '+' in name:
        for file in path.iterdir():
            if file.suffix == '.c' or file.suffix == '.cpp':
                components.append({
                    'header': None,
                    'source': str(file),
                    'driver': None,
                })
            elif file.suffix == '.h':
                components.append({
                    'header': str(file),
                    'source': None,
                    'driver': None,
                })
    else:
        for item in bde_items(path/'package'/(name + '.mem')):
            base   = path/item
            header = Path(str(base) + '.h')
            source = Path(str(base) + '.cpp')
            driver = Path(str(base) + '.t.cpp')
            components.append({
                'header': str(header) if header.is_file() else None,
                'source': str(source),
                'driver': str(driver) if driver.is_file() else None,
            })
    return components

class PackageResolver(Resolver[Package]):
    def __init__(self, group_path: Path) -> None:
        self._group_path = group_path

    def dependencies(self, name: str) -> Set[str]:
        return bde_items(self._group_path/name/'package'/(name + '.dep'))

    def resolve(self,
                name: str,
                resolved_packages: Mapping[str, Package]) -> Package:
        path       = self._group_path/name
        components = build_components(path)
        deps       = lookup_dependencies(name,
                                         self.dependencies,
                                         resolved_packages)
        return Package(str(path), deps, components)

class TargetResolver(Resolver[Target]):
    def __init__(self, config: Config, incl_test_deps: bool=False) -> None:
        self._roots                     = cast(List[Path], config['roots'])
        self._standalones               = cast(Set[str],
                                               set(config.get('standalones', [])))
        self._standalones |= {'standalones'}
        self._virtuals: Dict[str, str] = {}
        self._providers: Set[str]      = set()
        self._pkg_configs              = cast(Dict[str, str],
                                              config.get('pkg_configs', {}))
        self._extra_dependencies       = cast(Dict[str, List[str]],
                                              config.get('extra_dependencies',
                                                         {}))
        self._plugin_tests             = cast(Set[str],
                                              set(config.get('plugin_tests', [])))
        self._incl_test_deps           = incl_test_deps

        providers = config.get('providers', {})
        assert isinstance(providers, dict)
        provideds: Set[str] = set()
        for provider, all_provided in providers.items():
            provideds |= set(all_provided)
            for provided in all_provided:
                self._virtuals[provided] = provider

        self._providers = set(providers.keys()) - provideds

        runtime_libs = cast(List[str], config.get('runtime_libraries', []))
        self._runtime_libraries = set(runtime_libs)

    @staticmethod
    def _is_group(root: Path, name: str) -> Optional[Path]:
        path = root/'groups'/name
        if path.is_dir() and (path/'group').is_dir():
            return path
        return None

    def _is_standalone(self, root: Path, name: str) -> Optional[Path]:
        for category in self._standalones:
            path = root/category/name
            if path.is_dir() and (path/'package').is_dir():
                return path
        return None

    def _is_application(self, root: Path, name: str) -> Optional[Path]:
        path = root/'applications'/name
        if path.is_dir() and (path/'package').is_dir() \
                         and (path/f'{name}.m.cpp').is_file():
            return path
        return None

    @staticmethod
    def _is_cmake(root: Path, name: str) -> Optional[Path]:
        if root.stem == name and (root/'CMakeLists.txt').is_file():
            return root
        path = root/'thirdparty'/name
        if path.is_dir() and (path/'CMakeLists.txt').is_file():
            return path
        return None

    def identify(self, name: str) -> Identification:
        for root in self._roots:
            path = TargetResolver._is_group(root, name)
            if path is not None:
                return Identification('group', path)

            path = self._is_standalone(root, name)
            if path is not None:
                return Identification('package', path)

            path = self._is_application(root, name)
            if path is not None:
                return Identification('application', path)

            path = TargetResolver._is_cmake(root, name)
            if path is not None:
                return Identification('cmake', path)

        if name in self._virtuals:
            return Identification('virtual')

        if name in self._pkg_configs:
            return Identification('pkg_config', None, self._pkg_configs[name])

        raise TargetNotFoundError(name)

    def dependencies(self, name: str) -> Set[str]:
        target = self.identify(name)

        result = set()
        if name in self._virtuals:
            result.add(self._virtuals[name])
        if target.type in {'application', 'group', 'package'}:
            if target.type == 'application':
                meta_directory = 'package'
            else:
                meta_directory = target.type

            assert isinstance(target.path, Path)
            result |= bde_items(target.path/meta_directory/(name + '.dep'))
            if self._incl_test_deps:
                test_deps_path = target.path/meta_directory/(name + '.t.dep')
                if test_deps_path.is_file():
                    result |= bde_items(test_deps_path)
        result |= set(self._extra_dependencies.get(name, []))
        return result

    @staticmethod
    def _add_override(identification: Identification,
                      name: str,
                      target: Target) -> None:
        assert(identification.path is not None)
        overrides = identification.path/(name + '.cmake')
        if overrides.is_file():
            target.overrides = str(overrides)

    def resolve(self, name: str, seen: Dict[str, Target]) -> Target:
        deps = lookup_dependencies(name, self.dependencies, seen)

        identification = self.identify(name)

        result: Target
        if identification.type == 'group':
            assert isinstance(identification.path, Path)
            path = identification.path/'group'/(name + '.mem')
            packages = resolve(PackageResolver(identification.path),
                               list(bde_items(path)))
            result = Group(str(identification.path), deps, packages)
            TargetResolver._add_override(identification, name, result)
        elif identification.type == 'package':
            assert isinstance(identification.path, Path)
            components = build_components(identification.path)
            result = Package(str(identification.path), deps, components)
            TargetResolver._add_override(identification, name, result)
        elif identification.type == 'application':
            assert isinstance(identification.path, Path)
            components = build_components(identification.path)
            main_file = str(identification.path/f'{name}.m.cpp')
            if main_file not in {c['source'] for c in components}:
                components.append({
                    'header': None,
                    'source': main_file,
                    'driver': None,
                })
            result = Application(str(identification.path), deps, components)
            TargetResolver._add_override(identification, name, result)
        elif identification.type == 'cmake':
            result = CMake(name, str(identification.path), deps)
        elif identification.type == 'pkg_config':
            assert isinstance(identification.package, str)
            result = Pkg(name, identification.package, deps)
        elif identification.type == 'virtual':
            result = Target(name, deps)
        else: # pragma: no cover
            raise AssertionError(f'Unknown type: {identification.type}')

        if name in self._providers:
            result.has_output = False

        if any(d.name in self._runtime_libraries for d in deps):
            result.lazily_bound = True

        if name in self._plugin_tests:
            result.plugin_tests = True

        return result

