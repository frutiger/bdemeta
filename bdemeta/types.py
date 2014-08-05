import os
from itertools import chain

from bdemeta.graph import traverse, tsort

class Unit(object):
    def __init__(self, resolver, name, dependencies, cflags, ldflags):
        self._resolver     = resolver
        self._name         = name
        self._dependencies = dependencies
        self._cflags       = cflags
        self._ldflags      = ldflags

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

    def cflags(self):
        return self._cflags

    def ldflags(self):
        return self._ldflags

    def components(self):
        return {}

    def result_type(self):
        return None

class Package(Unit):
    def __init__(self, resolver, path, members, dependencies, cflags, ldflags):
        self._path    = path
        self._members = members
        name          = os.path.basename(path)
        super(Package, self).__init__(resolver,
                                      name,
                                      dependencies,
                                      cflags,
                                      ldflags)

    def path(self):
        return self._path

    def cflags(self):
        return ' '.join(self._cflags[:] + ['-I{}'.format(self._path)])

    def ldflags(self):
        return ' '.join(self._ldflags[:])

    def members(self):
        return self._members

class Group(Unit):
    def __init__(self, resolver, path, members, dependencies, cflags, ldflags):
        self._path    = path
        self._members = members
        name          = os.path.basename(path)
        super(Group, self).__init__(resolver,
                                    name,
                                    dependencies,
                                    cflags,
                                    ldflags)

    def _packages(self):
        return tsort(self._resolver(member) for member in self._members)

    def cflags(self):
        flags = self._cflags + [p.cflags() for p in self._packages()]
        return [flag for flag in flags if flag != '']

    def ldflags(self):
        flags = self._ldflags + [p.ldflags() for p in self._packages()] \
                              + ['-Lout/libs', '-l' + self._name]
        return [flag for flag in flags if flag != '']

    def components(self):
        deps = tsort(traverse(frozenset((self,))))
        deps.remove(self)
        deps_cflags  = list(chain(*[d.cflags()  for d in deps]))
        deps_ldflags = list(chain(*[d.ldflags() for d in deps]))

        result = []
        for package in self._packages():
            package_deps    = tsort(traverse(frozenset((package,))))
            package_cflags  = [p.cflags()  for p in package_deps \
                                                          if p.cflags()  != '']
            package_ldflags = [p.ldflags() for p in package_deps \
                                                          if p.ldflags() != '']

            group_cflags  =                  self._cflags
            group_ldflags = self.ldflags() + self._ldflags

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
    def __init__(self, resolver, path, members, dependencies, cflags, ldflags):
        self._path    = path
        self._members = members
        name          = os.path.basename(path)
        super(Application, self).__init__(resolver,
                                          name,
                                          dependencies,
                                          cflags,
                                          ldflags)

    def cflags(self):
        return self._cflags

    def ldflags(self):
        return self._ldflags

    def components(self):
        deps = tsort(traverse(frozenset((self,))))
        cflags  = self._cflags  + list(chain(*[d.cflags()  for d in deps]))
        ldflags = self._ldflags + list(chain(*[d.ldflags() for d in deps]))

        inputs = ' '.join((os.path.join(self._path, m + '.cpp') \
                                               for m in sorted(self._members)))
        return ({
            'cflags':  ' ' + ' '.join(cflags) if cflags else '',
            'input':   inputs,
            'ldflags': ' ' + ' '.join(ldflags) if ldflags else '',
        },)

    def result_type(self):
        return 'executable'

