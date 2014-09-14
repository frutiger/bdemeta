from collections import defaultdict
from unittest    import TestCase
import os

from bdemeta.types import Unit, Package, Group, Application

def dict_resolver(resolutions):
    return lambda name: resolutions[name]

class TestUnit(TestCase):
    def test_equality(self):
        a1 = Unit(None, 'a', None, None, None)
        a2 = Unit(None, 'a', None, None, None)
        b1 = Unit(None, 'b', None, None, None)
        b2 = Unit(None, 'b', None, None, None)

        assert(a1 == a2)
        assert(not a1 != a2)
        assert(a1 != b1)
        assert(a1 != b2)

        assert(a2 != b1)
        assert(a2 != b2)
        assert(a2 == a1)
        assert(not a2 != a1)

        assert(b1 == b2)
        assert(not b1 != b2)
        assert(b1 != a1)
        assert(b1 != a2)

        assert(b2 != a1)
        assert(b2 != a2)
        assert(b2 == b1)
        assert(not b2 != b1)

    def test_hash(self):
        a1 = Unit(None, 'a', None, None, None)
        a2 = Unit(None, 'a', None, None, None)
        b1 = Unit(None, 'b', None, None, None)
        b2 = Unit(None, 'b', None, None, None)

        assert(hash(a1) == hash(a2))
        assert(hash(a1) != hash(b1))
        assert(hash(a1) != hash(b2))

        assert(hash(a2) != hash(b1))
        assert(hash(a2) != hash(b2))
        assert(hash(a2) == hash(a1))

        assert(hash(b1) == hash(b2))
        assert(hash(b1) != hash(a1))
        assert(hash(b1) != hash(a2))

        assert(hash(b2) != hash(a1))
        assert(hash(b2) != hash(a2))
        assert(hash(b2) == hash(b1))

    def test_name(self):
        u = Unit(None, 'a', None, None, None)
        assert(u.name() == 'a')

    def test_flags(self):
        u = Unit(None, None, None, 5, None)
        assert(u.external_cflags() == 5)

    def test_dependencies(self):
        resolver = dict_resolver({ 'b': 5 })
        u = Unit(resolver, None, ('b'), None, None)
        dependencies = u.dependencies()
        assert(len(dependencies) == 1)
        assert(5 in dependencies)

    def test_components(self):
        u = Unit(None, None, None, None, None)
        assert(u.components() == {})

    def test_result_type(self):
        u = Unit(None, None, None, None, None)
        assert(u.result_type() == None)

class TestPackage(TestCase):
    empty_flags = {
        'internal': [],
        'external': [],
    }

    def test_name(self):
        path = os.path.join('foo', 'bar')
        p = Package(None, path, None, None, self.empty_flags, self.empty_flags)
        assert(p.name() == 'bar')

    def test_path(self):
        path = os.path.join('foo', 'bar')
        p = Package(None, path, None, None, self.empty_flags, self.empty_flags)
        assert(p.path() == path)

    def test_components(self):
        path = os.path.join('foo', 'bar')
        p = Package(None, path, None, None, self.empty_flags, self.empty_flags)
        assert(p.components() == {})

    def test_result_type(self):
        path = os.path.join('foo', 'bar')
        p = Package(None, path, None, None, self.empty_flags, self.empty_flags)
        assert(p.result_type() == None)

    def test_default_cflags(self):
        path = os.path.join('foo', 'bar')
        p = Package(None, path, None, None, self.empty_flags, self.empty_flags)
        assert(p.internal_cflags() == '-I{}'.format(path))
        assert(p.external_cflags() == '-I{}'.format(path))

    def test_custom_internal_cflags(self):
        path = os.path.join('foo', 'bar')
        p = Package(None,
                    path,
                    None,
                    None,
                    {
                        'internal': ['foo'],
                        'external': [],
                    },
                    self.empty_flags)
        # note that custom flags precede default flags
        assert(p.internal_cflags() == 'foo -I{}'.format(path))
        # note that internal flags do not appear as external flags
        assert(p.external_cflags() == '-I{}'.format(path))

    def test_custom_external_cflags(self):
        path = os.path.join('foo', 'bar')
        p = Package(None,
                    path,
                    None,
                    None,
                    {
                        'internal': [],
                        'external': ['bar'],
                    },
                    self.empty_flags)
        # note that external flags appear as internal flags
        assert(p.internal_cflags() == 'bar -I{}'.format(path))
        assert(p.external_cflags() == 'bar -I{}'.format(path))

    def test_custom_internal_and_external_cflags(self):
        path = os.path.join('foo', 'bar')
        p = Package(None,
                    path,
                    None,
                    None,
                    {
                        'internal': ['foo'],
                        'external': ['bar'],
                    },
                    self.empty_flags)
        # note that internal flags precede external flags
        assert(p.internal_cflags() == 'foo bar -I{}'.format(path))
        assert(p.external_cflags() == 'bar -I{}'.format(path))

    def test_default_ldflags(self):
        path = os.path.join('foo', 'bar')
        p = Package(None, path, None, None, self.empty_flags, self.empty_flags)
        assert(p.internal_ldflags() == '')
        assert(p.external_ldflags() == '')

    def test_custom_internal_ldflags(self):
        path = os.path.join('foo', 'bar')
        p = Package(None,
                    path,
                    None,
                    None,
                    self.empty_flags,
                    {
                        'internal': ['foo'],
                        'external': [],
                    })
        assert(p.internal_ldflags() == 'foo')
        # note that internal flags do not appear as external flags
        assert(p.external_ldflags() == '')

    def test_custom_external_ldflags(self):
        path = os.path.join('foo', 'bar')
        p = Package(None,
                    path,
                    None,
                    None,
                    self.empty_flags,
                    {
                        'internal': [],
                        'external': ['bar'],
                    })
        # note that external flags appear as internal flags
        assert(p.internal_ldflags() == 'bar')
        assert(p.external_ldflags() == 'bar')

    def test_custom_internal_and_external_ldflags(self):
        path = os.path.join('foo', 'bar')
        p = Package(None,
                    path,
                    None,
                    None,
                    self.empty_flags,
                    {
                        'internal': ['foo'],
                        'external': ['bar'],
                    })
        # note that external flags appear as internal flags
        assert(p.internal_ldflags() == 'foo bar')
        assert(p.external_ldflags() == 'bar')

    def test_members(self):
        path    = os.path.join('foo', 'bar')
        members = ['a', 'b']
        p = Package(None,
                    path,
                    members,
                    None,
                    self.empty_flags,
                    self.empty_flags)
        assert(p.members() == members)

class TestGroup(TestCase):
    empty_flags = {
        'internal': [],
        'external': [],
    }

    def test_name(self):
        path = os.path.join('foo', 'bar')
        g = Group(None, path, None, None, self.empty_flags, self.empty_flags)
        assert(g.name() == 'bar')

    def test_result_type(self):
        path = os.path.join('foo', 'bar')
        g = Group(None, path, None, None, self.empty_flags, self.empty_flags)
        assert(g.result_type() == 'library')

    def test_default_cflags(self):
        path = os.path.join('gr1', 'gr1pkg1')
        pkg1 = Package(None, path, [], [], self.empty_flags, self.empty_flags)

        resolver = dict_resolver({ 'gr1pkg1': pkg1 })

        path = os.path.join('gr1')
        g = Group(resolver,
                  path,
                  frozenset(['gr1pkg1']),
                  None,
                  self.empty_flags,
                  self.empty_flags)
        assert(g.external_cflags() == ['-Igr1/gr1pkg1'])

    def test_custom_internal_cflags(self):
        path = os.path.join('gr1', 'gr1pkg1')
        pkg1 = Package(None, path, [], [], self.empty_flags, self.empty_flags)

        resolver = dict_resolver({ 'gr1pkg1': pkg1 })

        path = os.path.join('gr1')
        g = Group(resolver,
                  path,
                  frozenset(['gr1pkg1']),
                  None,
                  {
                      'internal': ['foo'],
                      'external': [],
                  },
                  self.empty_flags)
        # note that internal flags do not appear as external flags
        assert(g.external_cflags() == ['-Igr1/gr1pkg1'])

    def test_custom_external_cflags(self):
        path = os.path.join('gr1', 'gr1pkg1')
        pkg1 = Package(None, path, [], [], self.empty_flags, self.empty_flags)

        resolver = dict_resolver({ 'gr1pkg1': pkg1 })

        path = os.path.join('gr1')
        g = Group(resolver,
                  path,
                  frozenset(['gr1pkg1']),
                  None,
                  {
                      'internal': [],
                      'external': ['bar'],
                  },
                  self.empty_flags)
        # note that custom flags precede default flags
        assert(g.external_cflags() == ['bar', '-Igr1/gr1pkg1'])

    def test_custom_internal_and_external_cflags(self):
        path = os.path.join('gr1', 'gr1pkg1')
        pkg1 = Package(None, path, [], [], self.empty_flags, self.empty_flags)

        resolver = dict_resolver({ 'gr1pkg1': pkg1 })

        path = os.path.join('gr1')
        g = Group(resolver,
                  path,
                  frozenset(['gr1pkg1']),
                  None,
                  {
                      'internal': ['foo'],
                      'external': ['bar'],
                  },
                  self.empty_flags)
        # note that internal flags do not appear as external flags
        assert(g.external_cflags() == ['bar', '-Igr1/gr1pkg1'])

    def test_default_ldflags(self):
        path = os.path.join('gr1', 'gr1pkg1')
        pkg1 = Package(None, path, [], [], self.empty_flags, self.empty_flags)

        resolver = dict_resolver({ 'gr1pkg1': pkg1 })

        path = os.path.join('gr1')
        g = Group(resolver,
                  path,
                  frozenset(['gr1pkg1']),
                  None,
                  self.empty_flags,
                  self.empty_flags)
        assert(g.external_ldflags() == ['out/libs/libgr1.a'])

    def test_custom_internal_ldflags(self):
        path = os.path.join('gr1', 'gr1pkg1')
        pkg1 = Package(None, path, [], [], self.empty_flags, self.empty_flags)

        resolver = dict_resolver({ 'gr1pkg1': pkg1 })

        path = os.path.join('gr1')
        g = Group(resolver,
                  path,
                  frozenset(['gr1pkg1']),
                  None,
                  self.empty_flags,
                  {
                      'internal': [],
                      'external': ['bar'],
                  })
        # note that internal flags do not appear as external flags
        assert(g.external_ldflags() == ['bar', 'out/libs/libgr1.a'])

    def test_custom_external_ldflags(self):
        path = os.path.join('gr1', 'gr1pkg1')
        pkg1 = Package(None, path, [], [], self.empty_flags, self.empty_flags)

        resolver = dict_resolver({ 'gr1pkg1': pkg1 })

        path = os.path.join('gr1')
        g = Group(resolver,
                  path,
                  frozenset(['gr1pkg1']),
                  None,
                  self.empty_flags,
                  {
                      'internal': ['foo'],
                      'external': [],
                  })
        # note that custom flags precede default flags
        assert(g.external_ldflags() == ['out/libs/libgr1.a'])

    def test_custom_internal_and_external_ldflags(self):
        path = os.path.join('gr1', 'gr1pkg1')
        pkg1 = Package(None, path, [], [], self.empty_flags, self.empty_flags)

        resolver = dict_resolver({ 'gr1pkg1': pkg1 })

        path = os.path.join('gr1')
        g = Group(resolver,
                  path,
                  frozenset(['gr1pkg1']),
                  None,
                  self.empty_flags,
                  {
                      'internal': ['foo'],
                      'external': ['bar'],
                  })
        # note that internal flags do not appear as external flags
        assert(g.external_ldflags() == ['bar', 'out/libs/libgr1.a'])

    def test_components_without_driver(self):
        pjoin = os.path.join
        path  = pjoin('gr1', 'gr1pkg1')
        pkg1  = Package(None,
                        path,
                       [{'name': 'gr1pkg1_c1',
                         'path':   pjoin(path, 'gr1pkg1_c1.cpp'),
                         'driver': None,
                       }],
                       [],
                        self.empty_flags,
                        self.empty_flags)

        resolver = dict_resolver({ 'gr1pkg1': pkg1 })

        path = os.path.join('gr1')
        g = Group(resolver,
                  path,
                  frozenset(['gr1pkg1']),
                  [],
                  self.empty_flags,
                  self.empty_flags)
        assert(g.components() == ({
            'type':   'object',
            'input':  'gr1/gr1pkg1/gr1pkg1_c1.cpp',
            'cflags': ' -Igr1/gr1pkg1',
            'output': 'gr1pkg1_c1.o',
        },))

    def test_components_without_driver_with_internal_cflags(self):
        pjoin = os.path.join
        path  = pjoin('gr1', 'gr1pkg1')
        pkg1  = Package(None,
                        path,
                       [{'name': 'gr1pkg1_c1',
                         'path':   pjoin(path, 'gr1pkg1_c1.cpp'),
                         'driver': None,
                       }],
                       [],
                       {
                           'internal': ['foo'],
                           'external': [],
                       },
                        self.empty_flags)

        resolver = dict_resolver({ 'gr1pkg1': pkg1 })

        path = os.path.join('gr1')
        g = Group(resolver,
                  path,
                  frozenset(['gr1pkg1']),
                  [],
                  self.empty_flags,
                  self.empty_flags)
        assert(g.components() == ({
            'type':   'object',
            'input':  'gr1/gr1pkg1/gr1pkg1_c1.cpp',
            # note that the internal cflag appeared
            'cflags': ' foo -Igr1/gr1pkg1',
            'output': 'gr1pkg1_c1.o',
        },))

    def test_components_with_driver(self):
        pjoin = os.path.join
        path  = pjoin('gr1', 'gr1pkg1')
        pkg1  = Package(None,
                        path,
                       [{'name':  'gr1pkg1_c1',
                         'path':   pjoin(path, 'gr1pkg1_c1.cpp'),
                         'driver': pjoin(path, 'gr1pkg1_c1.t.cpp'),
                       }],
                       [],
                        self.empty_flags,
                        self.empty_flags)

        resolver = dict_resolver({ 'gr1pkg1': pkg1 })

        path = os.path.join('gr1')
        g = Group(resolver,
                  path,
                  frozenset(['gr1pkg1']),
                  [],
                  self.empty_flags,
                  self.empty_flags)
        assert(g.components() == ({
            'type':   'object',
            'input':  'gr1/gr1pkg1/gr1pkg1_c1.cpp',
            'cflags': ' -Igr1/gr1pkg1',
            'output': 'gr1pkg1_c1.o',
        }, {
            'type':    'test',
            'input':   'gr1/gr1pkg1/gr1pkg1_c1.t.cpp',
            'cflags':  ' -Igr1/gr1pkg1',
            'ldflags': ' out/libs/libgr1.a',
            'output':  'gr1pkg1_c1.t',
        }))

class TestApplication(TestCase):
    empty_flags = {
        'internal': [],
        'external': [],
    }

    def test_name(self):
        path = os.path.join('foo', 'bar')
        a = Application(None,
                        path,
                        None,
                        None,
                        self.empty_flags,
                        self.empty_flags)
        assert(a.name() == 'bar')

    def test_result_type(self):
        path = os.path.join('foo', 'bar')
        a = Application(None,
                        path,
                        None,
                        None,
                        self.empty_flags,
                        self.empty_flags)
        assert(a.result_type() == 'executable')

    def test_user_flags(self):
        a = Application(None,
                       'gr1',
                        [],
                        [],
                        {
                            'external': ['5'],
                            'internal': [],
                        },
                        self.empty_flags)
        assert(a.external_cflags() == ['5'])

    def test_no_dependency_components(self):
        path = os.path.join('foo', 'bar')
        a = Application(None,
                        path,
                       ['a', 'b'],
                       [],
                        self.empty_flags,
                        self.empty_flags)
        assert(a.components() == ({
            'input':   'foo/bar/a.cpp foo/bar/b.cpp',
            'cflags':  '',
            'ldflags': '',
        },))

    def test_dependency_components(self):
        gr1 = Group(None, 'gr1', [], [], self.empty_flags, self.empty_flags)

        resolver = dict_resolver({ 'gr1': gr1 })

        a = Application(resolver,
                       'baz',
                      ['a'],
                      ['gr1'],
                        self.empty_flags,
                        self.empty_flags)
        assert(a.components() == ({
            'input':   'baz/a.cpp',
            'cflags':  '',
            'ldflags': ' out/libs/libgr1.a',
        },))

