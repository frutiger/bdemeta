# bdemeta.types

import collections
import os

def concat(*lists):
    # TBD: move
    result = []
    for l in lists:
        result = result + l
    return result

Component = collections.namedtuple('Component', ['name', 'source', 'driver'])

Source = collections.namedtuple('Source', ['type',
                                           'name',
                                           'input',
                                           'compiler',
                                           'flags',
                                           'output'])

class Buildable(object):
    def __init__(self, internal_cflags, external_cflags):
        self._internal_cflags = internal_cflags
        self._external_cflags = external_cflags

    def internal_cflags(self):
        return self._internal_cflags

    def external_cflags(self):
        return self._external_cflags

class Node(str):
    def __new__(cls, name, *args):
        return str.__new__(cls, name)

    def __init__(self, name, dependencies):
        self._dependencies = dependencies

    def dependencies(self):
        return self._dependencies

class Unit(Node, Buildable):
    def __init__(self, name, dependencies, internal_cflags, external_cflags):
        Node.__init__(self, name, dependencies)
        Buildable.__init__(self, internal_cflags, external_cflags)

    def cflags(self):
        return self._external_cflags

    def ld_args(self):
        return []

    def ld_input(self):
        return []

class Package(Unit):
    def __new__(cls, path, *args):
        return str.__new__(cls, os.path.basename(path))

    def __init__(self,
                 path,
                 dependencies,
                 internal_cflags,
                 external_cflags,
                 components):
        Unit.__init__(self,
                      os.path.basename(path),
                      dependencies,
                      internal_cflags,
                      external_cflags + ['-I' + path])
        self._components = components

    def components(self):
        return self._components

class Target(Unit):
    def __init__(self,
                 name,
                 dependencies,
                 internal_cflags,
                 external_cflags,
                 sources,
                 ld_args,
                 output):
        Unit.__init__(self,
                      name,
                      dependencies,
                      internal_cflags,
                      external_cflags)
        self._sources = sources
        self._ld_args = ld_args
        self._output  = output

    def sources(self):
        return self._sources

    def objects(self):
        return sorted([s.output for s in self._sources if s.type == 'object'])

    def unit_tests(self):
        return []

    def ld_args(self):
        return self._ld_args

    def output(self):
        return self._output

    def ld_input(self):
        return ([self._output] if self._output else []) + self._ld_args

class Group(Target):
    def __new__(cls, path, *args):
        return str.__new__(cls, os.path.basename(path))

    def __init__(self,
                 path,
                 dependencies,
                 internal_cflags,
                 external_cflags,
                 packages,
                 ld_args):
        name    = os.path.basename(path)
        sources = []
        Target.__init__(self,
                        name,
                        dependencies,
                        internal_cflags,
                        external_cflags,
                        sources,
                        ld_args,
                        os.path.join('out', 'libs', 'lib' + name + '.a'))
        self._packages = packages

        ld_input = concat(self.ld_input(),
                          *[u.ld_input() for u in dependencies])
        ld_input = ' ' + ' '.join(ld_input) if ld_input else ''

        for package in reversed(packages):
            flags = concat(package.internal_cflags(),
                           package.external_cflags(),
                           *[p.cflags() for p in package.dependencies()])
            flags = concat(flags,
                           self.internal_cflags(),
                           self.external_cflags(),
                           *[u.cflags() for u in dependencies])

            for c in package.components():
                sources.append(
                        Source('object',
                                c.name + '.o',
                                c.source,
                               'cxx' if c.source[-4:] == '.cpp' else 'cc',
                               ' ' + ' '.join(flags) if flags else '',
                                os.path.join('out', 'objs', c.name + '.o')))
                if c.driver:
                    sources.append(
                       Source('executable',
                               c.name + '.t',
                               c.driver + ld_input,
                              'cxx',
                              ' ' + ' '.join(flags) if flags else '',
                               os.path.join('out', 'tests', c.name + '.t')))

    def cflags(self):
        return concat(self.external_cflags(),
                      *[p.external_cflags() for p in self._packages])

    def unit_tests(self):
        return sorted([s.output for s in self._sources \
                                                    if s.type == 'executable'])

class Application(Target):
    def __new__(cls, path, *args):
        return str.__new__(cls, os.path.basename(path))

    def __init__(self,
                 path,
                 dependencies,
                 internal_cflags,
                 external_cflags,
                 ld_args):
        name    = os.path.basename(path)
        sources = []
        Target.__init__(self,
                        name,
                        dependencies,
                        internal_cflags,
                        external_cflags,
                        sources,
                        ld_args,
                        os.path.join('out', 'apps', name))

        flags = concat(self.internal_cflags(),
                       self.external_cflags(),
                       *[u.cflags() for u in dependencies])

        ld_input = concat(self._ld_args,
                          *[u.ld_input() for u in dependencies])
        ld_input = ' ' + ' '.join(ld_input) if ld_input else ''

        sources.append(
                    Source('executable',
                            str(self),
                            os.path.join(path, name[2:] + '.m.cpp') + ld_input,
                           'cxx',
                           ' ' + ' '.join(flags) if flags else '',
                            self._output))

