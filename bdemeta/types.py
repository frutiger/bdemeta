# bdemeta.types

import os

class Unit(str):
    def __new__(cls, name, *args):
        return str.__new__(cls, name)

    def __init__(self, name, dependencies):
        self._dependencies = dependencies
        self.has_output    = True
        self.lazily_bound  = False

    def dependencies(self):
        return self._dependencies

class Package(Unit):
    def __new__(cls, path, *args):
        return Unit.__new__(cls, os.path.basename(path))

    def __init__(self, path, dependencies, components):
        Unit.__init__(self, str(self), dependencies)
        self._path       = path
        self._components = components

    def includes(self):
        yield self._path

    def headers(self):
        for component in self._components:
            if component['header']:
                yield component['header']

    def sources(self):
        for component in self._components:
            if component['source']:
                yield component['source']

    def drivers(self):
        for component in self._components:
            if component['driver']:
                yield component['driver']

class Group(Unit):
    def __new__(cls, path, *args):
        return Unit.__new__(cls, os.path.basename(path))

    def __init__(self, path, dependencies, packages):
        Unit.__init__(self, str(self), dependencies)
        self._path     = path
        self._packages = list(packages)

    def includes(self):
        for package in self._packages:
            yield os.path.join(self._path, package)

    def headers(self):
        for package in self._packages:
            for header in package.headers():
                yield header

    def sources(self):
        for package in self._packages:
            for source in package.sources():
                yield source

    def drivers(self):
        for package in self._packages:
            for driver in package.drivers():
                yield driver

class CMake(Unit):
    def __new__(cls, name, path, *args):
        return Unit.__new__(cls, name)

    def __init__(self, name, path):
        Unit.__init__(self, str(self), [])
        self._path = path

    def path(self):
        return self._path

