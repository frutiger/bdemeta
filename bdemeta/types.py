# bdemeta.types

import os

class Unit(str):
    def __new__(cls, name, *args):
        return str.__new__(cls, name)

    def __init__(self, name, dependencies):
        self._dependencies = dependencies

    def dependencies(self):
        return self._dependencies

class Package(Unit):
    def __new__(cls, path, *args):
        return str.__new__(cls, os.path.basename(path))

    def __init__(self, path, dependencies, sources, drivers):
        Unit.__init__(self, str(self), dependencies)
        self._path    = path
        self._sources = sources
        self._drivers = drivers

    def includes(self):
        yield f'{self._path}'

    def components(self):
        return self._sources

    def drivers(self):
        return self._drivers

    def sources(self):
        for source in self._sources:
            yield source

class Group(Unit):
    def __new__(cls, path, *args):
        return str.__new__(cls, os.path.basename(path))

    def __init__(self, path, dependencies, packages):
        Unit.__init__(self, str(self), dependencies)
        self._path     = path
        self._packages = list(packages)

    def includes(self):
        for package in self._packages:
            yield os.path.join(self._path, package)

    def sources(self):
        for package in self._packages:
            for source in package.components():
                yield source

    def drivers(self):
        for package in self._packages:
            for driver in package.drivers():
                yield driver

class CMake(Unit):
    def __new__(cls, path, *args):
        return str.__new__(cls, os.path.basename(path))

    def __init__(self, path):
        Unit.__init__(self, str(self), [])
        self._path = path

    def path(self):
        return self._path

