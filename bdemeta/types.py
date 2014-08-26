import os
from itertools import chain

from bdemeta.graph import traverse, tsort

class Unit(object):
    def __init__(self, resolver, name, dependencies, flags):
        self._resolver     = resolver
        self._name         = name
        self._dependencies = dependencies
        self._flags        = flags

    def __eq__(self, other):
        return self._name == other._name

    def __ne__(self, other):
        # Note: in Python 2, != is not defined as not ==, so we must implement
        # this method
        return not self == other

    def __hash__(self):
        return hash(self._name)

    def name(self):
        return self._name

    def dependencies(self):
        return frozenset(self._resolver(name) for name in self._dependencies)

    def flags(self, type):
        return self._flags[type]

    def components(self):
        return {}

    def result_type(self):
        return None

class Package(Unit):
    def __init__(self, resolver, path, members, dependencies, flags):
        self._path    = path
        self._members = members
        name          = os.path.basename(path)
        super(Package, self).__init__(resolver, name, dependencies, flags)

    def path(self):
        return self._path

    def flags(self, type):
        flags = self._flags[type][:]
        if type == 'c':
            flags.append('-I{}'.format(self._path))
        return ' '.join(flags)

    def members(self):
        return self._members

class Group(Unit):
    def __init__(self, resolver, path, members, dependencies, flags):
        self._path    = path
        self._members = members
        name          = os.path.basename(path)
        super(Group, self).__init__(resolver, name, dependencies, flags)

    def _packages(self):
        return tsort(self._resolver(member) for member in self._members)

    def flags(self, type):
        flags = []
        flags = flags + self._flags[type]
        flags = flags + [p.flags(type) for p in self._packages()]
        if type == 'ld':
            flags = flags + ['-Lout/libs', '-l' + self._name]
        return list(filter(lambda x: x != '', flags))

    def components(self):
        deps = tsort(traverse(frozenset((self,))))
        deps.remove(self)
        deps_cflags  = list(chain(*[d.flags('c')  for d in deps]))
        deps_ldflags = list(chain(*[d.flags('ld') for d in deps]))

        result = []
        for package in self._packages():
            package_deps    = tsort(traverse(frozenset((package,))))
            package_cflags  = [p.flags('c')  for p in package_deps \
                                                        if p.flags('c')  != '']
            package_ldflags = [p.flags('ld') for p in package_deps \
                                                        if p.flags('ld') != '']

            group_cflags  =                    self._flags['c']
            group_ldflags = self.flags('ld') + self._flags['ld']

            cflags  = list(sorted(chain(package_cflags,
                                        group_cflags,
                                        deps_cflags)))
            ldflags = list(sorted(chain(package_ldflags,
                                        group_ldflags,
                                        deps_ldflags)))

            for m in package.members():
                result.append({
                    'type':   'object',
                    'input':   m['path'],
                    'cflags': ' ' + ' '.join(cflags) if cflags else '',
                    'output':  m['name'] + '.o',
                })
                if m['driver']:
                    result.append({
                        'type':    'test',
                        'input':    m['driver'],
                        'cflags':  ' ' + ' '.join(cflags)  if cflags else '',
                        'ldflags': ' ' + ' '.join(ldflags) if ldflags else '',
                        'output':   m['name'] + '.t',
                    })
        return tuple(result)

    def result_type(self):
        return 'library'

class Application(Unit):
    def __init__(self, resolver, path, members, dependencies, flags):
        self._path    = path
        self._members = members
        name          = os.path.basename(path)
        super(Application, self).__init__(resolver, name, dependencies, flags)

    def flags(self, type):
        return self._flags[type]

    def components(self):
        deps = tsort(traverse(frozenset((self,))))
        cflags  = self._flags['c']  + list(chain(*[d.flags('c')  \
                                                               for d in deps if d != self]))
        ldflags = self._flags['ld'] + list(chain(*[d.flags('ld') \
                                                               for d in deps if d != self]))

        inputs = ' '.join((os.path.join(self._path, m + '.cpp') \
                                               for m in sorted(self._members)))
        return ({
            'cflags':  ' ' + ' '.join(cflags) if cflags else '',
            'input':   inputs,
            'ldflags': ' ' + ' '.join(ldflags) if ldflags else '',
        },)

    def result_type(self):
        return 'executable'

