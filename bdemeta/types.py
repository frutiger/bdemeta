# bdemeta.types

import os
from pathlib import Path
from typing import Dict, Iterator, List, Optional, Sequence, Union

Config = Dict[str, Union[List[Path], List[str], Dict[str, str]]]

class Identification:
    def __init__(self,
                 type:    str,
                 path:    Optional[Path] = None,
                 package: Optional[str] = None) -> None:
        self.type    = type
        self.path    = path
        self.package = package

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Identification):
            return (self.type, self.path, self.package) == \
                                        (other.type, other.path, other.package)
        else:
            return False

class Target:
    def __init__(self, name: str, dependencies: Sequence['Target']) -> None:
        self.name                     = name
        self._dependencies            = dependencies
        self.has_output               = True
        self.lazily_bound             = False
        self.overrides: Optional[str] = None
        self.plugin_tests             = False

    def dependencies(self) -> Sequence['Target']:
        return self._dependencies

class Package(Target):
    def __init__(self,
                 path: str,
                 dependencies: Sequence[Target],
                 components: List[Dict[str, Optional[str]]]) -> None:
        Target.__init__(self, os.path.basename(path), dependencies)
        self._path       = path
        self._components = components

    def includes(self) -> Iterator[str]:
        yield self._path

    def headers(self) -> Iterator[str]:
        for component in self._components:
            if component['header'] is not None:
                yield component['header']

    def sources(self) -> Iterator[str]:
        for component in self._components:
            if component['source'] is not None:
                yield component['source']

    def drivers(self) -> Iterator[str]:
        for component in self._components:
            if component['driver'] is not None:
                yield component['driver']

class Application(Package):
    def __init__(self,
                 path: str,
                 dependencies: Sequence[Target],
                 components: List[Dict[str, Optional[str]]]) -> None:
        Package.__init__(self, path, dependencies, components)

class Group(Target):
    def __init__(self,
                 path: str,
                 dependencies: Sequence[Target],
                 packages: Sequence[Package]) -> None:
        Target.__init__(self, os.path.basename(path), dependencies)
        self._path     = path
        self._packages = list(packages)

    def includes(self) -> Iterator[str]:
        for package in self._packages:
            yield os.path.join(self._path, package.name)

    def headers(self) -> Iterator[str]:
        for package in self._packages:
            for header in package.headers():
                yield header

    def sources(self) -> Iterator[str]:
        for package in self._packages:
            for source in package.sources():
                yield source

    def drivers(self) -> Iterator[str]:
        for package in self._packages:
            for driver in package.drivers():
                yield driver

class CMake(Target):
    def __init__(self, name: str, path: str, deps: Sequence[Target]) -> None:
        Target.__init__(self, name, deps)
        self._path = path

    def path(self) -> str:
        return self._path

class Pkg(Target):
    def __init__(self,
                 name: str,
                 package: str,
                 deps: Sequence[Target]) -> None:
        Target.__init__(self, name, deps)
        self.package = package

