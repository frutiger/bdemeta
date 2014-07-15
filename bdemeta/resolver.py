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
    def __init__(self, roots, dependencies, flags):
        self._roots        = roots
        self._dependencies = dependencies
        self._flags        = flags

    @bdemeta.functional.memoize
    def __call__(self, name):
        if len(name) == 3:
            for root in self._roots:
                candidate = os.path.join(root.strip(), 'groups', name)
                if os.path.isdir(candidate):
                    members = bde_items(candidate, 'group', name + '.mem')
                    deps    = self._dependencies[name] | \
                                                       bde_items(candidate,
                                                                'group',
                                                                 name + '.dep')
                    return bdemeta.types.Group(self,
                                               candidate,
                                               members,
                                               deps,
                                               self._flags[name])
        else:
            group = name[:3]
            for root in self._roots:
                candidate = os.path.join(root.strip(), 'groups', group, name)
                if os.path.isdir(candidate):
                    if '+' in name:
                        members = os.listdir(candidate)
                    else:
                        members = bde_items(candidate,
                                           'package',
                                            name + '.mem')
                    deps = self._dependencies[name] | bde_items(candidate,
                                                               'package',
                                                                name + '.dep')
                    return bdemeta.types.Package(self,
                                                 candidate,
                                                 members,
                                                 deps,
                                                 self._flags[name])
        return bdemeta.types.Unit(self,
                                  name,
                                  self._dependencies[name],
                                  self._flags[name])

