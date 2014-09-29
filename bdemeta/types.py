import os
from itertools import chain

from bdemeta.graph import traverse, tsort

class Unit(object):
    def __init__(self,
                 resolver,
                 name,
                 dependencies,
                 external_cflags,
                 external_ldflags):
        self._resolver         = resolver
        self._name             = name
        self._dependencies     = dependencies
        self._external_cflags  = external_cflags
        self._external_ldflags = external_ldflags

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

    def external_cflags(self):
        return self._external_cflags

    def external_ldflags(self):
        return self._external_ldflags

    def components(self):
        return {}

    def result_type(self):
        return None

class Package(Unit):
    def __init__(self, resolver, path, members, dependencies, cflags, ldflags):
        self._path             = path
        self._members          = members
        self._internal_cflags  = cflags['internal'] \
                                                  + cflags['external'] \
                                                  + ['-I{}'.format(self._path)]
        self._internal_ldflags = ldflags['internal'] + ldflags['external']
        name                   = os.path.basename(path)
        super(Package, self).__init__(
                              resolver,
                              name,
                              dependencies,
                              cflags['external'] + ['-I{}'.format(self._path)],
                              ldflags['external'])

    def path(self):
        return self._path

    def internal_cflags(self):
        return ' '.join(self._internal_cflags)

    def external_cflags(self):
        return ' '.join(self._external_cflags)

    def internal_ldflags(self):
        return ' '.join(self._internal_ldflags)

    def external_ldflags(self):
        return ' '.join(self._external_ldflags)

    def members(self):
        return self._members

class Group(Unit):
    def __init__(self, resolver, path, members, dependencies, cflags, ldflags):
        self._path             = path
        self._members          = members
        self._internal_cflags  = cflags['internal'] + cflags['external']
        self._internal_ldflags = ldflags['internal']
        name                   = os.path.basename(path)
        super(Group, self).__init__(resolver,
                                    name,
                                    dependencies,
                                    cflags['external'],
                                    ldflags['external'])

    def _packages(self):
        return tsort(self._resolver(member) for member in self._members)

    def external_cflags(self):
        flags = self._external_cflags \
                              + [p.external_cflags() for p in self._packages()]
        return [flag for flag in flags if flag != '']

    def external_ldflags(self):
        flags = self._external_ldflags \
                           + [p.external_ldflags() for p in self._packages()] \
                           + ['out/libs/lib' + self._name + '.a']
        return [flag for flag in flags if flag != '']

    def components(self):
        deps = tsort(traverse(frozenset((self,))))
        deps.remove(self)
        deps_cflags  = list(chain(*[d.external_cflags()  for d in deps]))
        deps_ldflags = list(chain(*[d.external_ldflags() for d in deps]))

        result = []
        for package in self._packages():
            pkg_deps    = tsort(traverse(frozenset((package,))))

            package_cflags  = []
            package_cflags.append(package.internal_cflags())
            package_cflags.extend([p.external_cflags()  for p in pkg_deps \
                                                              if p != package])
            package_cflags = [f for f in package_cflags if f != '']

            package_ldflags  = []
            package_ldflags.append(package.internal_ldflags())
            package_ldflags.extend([p.external_ldflags()  for p in pkg_deps \
                                                              if p != package])
            package_ldflags = [f for f in package_ldflags if f != '']

            group_cflags  = self._internal_cflags
            group_ldflags = self._internal_ldflags + self.external_ldflags()

            cflags  = list(sorted(chain(package_cflags,
                                        group_cflags,
                                        deps_cflags)))
            ldflags = list(chain(package_ldflags, group_ldflags, deps_ldflags))

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
        self._path             = path
        self._members          = members
        self._internal_cflags  = cflags['internal']
        self._internal_ldflags = ldflags['internal']
        name                   = os.path.basename(path)
        super(Application, self).__init__(resolver,
                                          name,
                                          dependencies,
                                          cflags['external'],
                                          ldflags['external'])

    def external_cflags(self):
        return self._external_cflags

    def external_ldflags(self):
        return self._external_ldflags

    def components(self):
        deps = tsort(traverse(frozenset((self,))))
        cflags  = sorted(chain(self._internal_cflags,
                               *[d.external_cflags()  for d in deps]))
        ldflags = self._internal_ldflags \
                           + list(chain(*[d.external_ldflags() for d in deps]))

        inputs = ' '.join((os.path.join(self._path, m + '.cpp') \
                                               for m in sorted(self._members)))
        return ({
            'cflags':  ' ' + ' '.join(cflags) if cflags else '',
            'input':   inputs,
            'ldflags': ' ' + ' '.join(ldflags) if ldflags else '',
        },)

    def result_type(self):
        return 'executable'

