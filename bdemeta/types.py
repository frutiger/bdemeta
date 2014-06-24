import os
from itertools import chain

from bdemeta.graph import traverse, tsort

def bde_items(*args):
    items_filename = os.path.join(*args)
    items = []
    with open(items_filename) as items_file:
        for l in items_file:
            if len(l) > 1 and l[0] != '#':
                items = items + l.split()
    return frozenset(items)

class Unit(object):
    def __init__(self, resolver, name, dependencies, flags):
        self._resolver     = resolver
        self._name         = name
        self._dependencies = dependencies
        self._flags        = flags

    def __eq__(self, other):
        return self._name == other._name

    def __cmp__(self, other):
        return cmp(self._name, other._name)

    def __hash__(self):
        return hash(self._name)

    def name(self):
        return self._name

    def dependencies(self):
        return frozenset(self._resolver(name) for name in self._dependencies)

    def flags(self, type):
        return self._flags[type]

class Package(Unit):
    def __init__(self, resolver, path, dependencies, flags):
        self._path   = path
        name         = os.path.basename(path)
        dependencies = frozenset(dependencies)
        super(Package, self).__init__(
                      resolver,
                      name,
                      dependencies | bde_items(path, 'package', name + '.dep'),
                      flags)

    def path(self):
        return self._path

    def flags(self, type):
        flags = self._flags[type][:]
        if type == 'c':
            flags.append('-I{}'.format(self._path))
        return ' '.join(flags)

    def components(self):
        if '+' in self._name:
            # A '+' in a package name means all of its contents should
            # be put into the archive
            result = os.listdir(self._path)
            result = filter(lambda x: x[-4:] == '.cpp' or x[-2:] == '.c',
                            result)
            result = (os.path.join(self._path, f) for f in result)
            result = map(lambda f: os.path.relpath(f, self._path), result)
            return result
        else:
            return bde_items(self._path,
                            'package',
                             self._name + '.mem')

class Group(Unit):
    def __init__(self, resolver, path, dependencies, flags):
        self._path   = path
        name         = os.path.basename(path)
        dependencies = frozenset(dependencies)
        super(Group, self).__init__(
                        resolver,
                        name,
                        dependencies | bde_items(path, 'group', name + '.dep'),
                        flags)

    def _packages(self):
        names = bde_items(self._path, 'group', self._name + '.mem')
        return tsort(self._resolver(name) for name in names)

    def flags(self, type):
        flags = []
        if type == 'ld':
            flags = flags + ['-Lout/libs', '-l' + self._name]
        flags = flags + [p.flags(type) for p in self._packages()]
        flags = flags + self._flags[type]
        return list(filter(lambda x: x != '', flags))

    def components(self):
        deps = tsort(traverse(frozenset((self,))))
        deps.remove(self)
        deps_cflags  = list(chain(*[d.flags('c')  for d in deps]))
        deps_ldflags = list(chain(*[d.flags('ld') for d in deps]))

        result = {}
        for package in self._packages():
            package_deps    = tsort(traverse(frozenset((package,))))
            package_cflags  = [p.flags('c')  for p in package_deps]
            package_ldflags = [p.flags('ld') for p in package_deps]

            group_cflags  =                    self._flags['c']
            group_ldflags = self.flags('ld') + self._flags['ld']

            cflags  = list(chain(package_cflags,  group_cflags,  deps_cflags))
            ldflags = list(chain(package_ldflags, group_ldflags, deps_ldflags))

            if '+' in package.name():
                for c in package.components():
                    name, ext = os.path.splitext(c)
                    if ext == '.c' or ext == '.cpp':
                        result[c] = {
                            'cflags': cflags,
                            'source': os.path.join(package.path(), c),
                            'object': name + '.o',
                        }
            else:
                for c in package.components():
                    result[c] = {
                        'cflags':  cflags,
                        'ldflags': ldflags,
                        'source':  os.path.join(package.path(), c + '.cpp'),
                        'object':  c + '.o',
                        'driver':  os.path.join(package.path(), c + '.t.cpp'),
                        'test':    c + '.t',
                    }
        return result

