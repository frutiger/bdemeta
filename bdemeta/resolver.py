import os

import bdemeta.functional
import bdemeta.types

@bdemeta.functional.memoize
def bde_items(*args):
    items_filename = os.path.join(*args)
    items = []
    with open(items_filename) as items_file:
        for l in items_file:
            if len(l) > 1 and l[0] != '#':
                items = items + l.split()
    return frozenset(items)

class Resolver(object):
    def __init__(self, config):
        self._config = config

    @bdemeta.functional.memoize
    def __call__(self, name):
        for root in self._config['roots']:
            if len(name) == 3:
                candidate = os.path.join(root.strip(), 'groups', name)
                if os.path.isdir(candidate):
                    members = bde_items(candidate, 'group', name + '.mem')
                    deps    = frozenset(self._config['dependencies'][name]) | \
                                   bde_items(candidate, 'group', name + '.dep')
                    return bdemeta.types.Group(self,
                                               candidate,
                                               members,
                                               deps,
                                               self._config['cflags'][name],
                                               self._config['ldflags'][name])
            elif len(name) >= 3:
                group = name[:3]
                candidate = os.path.join(root.strip(), 'groups', group, name)
                cpp      = lambda x: x + '.cpp'
                tcpp     = lambda x: x + '.t.cpp'
                basename = os.path.basename
                if os.path.isdir(candidate):
                    if '+' in name:
                        ms = os.listdir(candidate)
                        ms = (os.path.splitext(m) for m in ms)
                        ms = (m for m in ms if m[1] == '.c' or m[1] == '.cpp')
                        ms = ({'name':   basename(candidate) + '_' + m[0],
                               'path':   os.path.join(candidate, m[0] + m[1]),
                               'driver': None} for m in ms)
                    else:
                        ms = bde_items(candidate, 'package', name + '.mem')
                        ms = ((m, os.path.join(candidate, m)) for m in ms)
                        ms = ({'name':   m[0],
                               'path':   cpp(m[1]),
                               'driver': os.path.isfile(tcpp(m[1])) and
                                                                     tcpp(m[1])
                              } for m in ms)
                    deps = frozenset(self._config['dependencies'][name]) | \
                                 bde_items(candidate, 'package', name + '.dep')
                    return bdemeta.types.Package(self,
                                                 candidate,
                                                 list(ms),
                                                 deps,
                                                 self._config['cflags'][name],
                                                 self._config['ldflags'][name])

        for root in self._config['roots']:
            candidate = os.path.join(root.strip(), 'applications', name)
            if os.path.isdir(candidate):
                members = bde_items(candidate, 'application', name + '.mem')
                deps    = frozenset(self._config['dependencies'][name]) | \
                             bde_items(candidate, 'application', name + '.dep')
                return bdemeta.types.Application(self,
                                                 candidate,
                                                 members,
                                                 deps,
                                                 self._config['cflags'][name],
                                                 self._config['ldflags'][name])

        return bdemeta.types.Unit(self,
                                  name,
                                  self._config['dependencies'][name],
                                  self._config['cflags'][name],
                                  self._config['ldflags'][name])

