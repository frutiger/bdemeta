# tests.test_resolver

from os.path  import join as pjoin
from unittest import TestCase

from bdemeta.resolver import bde_items, resolve, PackageResolver, UnitResolver
from tests.patcher    import OsPatcher

import bdemeta.resolver  # needed for the patcher to work

class BdeItemsTest(TestCase):
    def setUp(self):
        self._patcher = OsPatcher([bdemeta.resolver], {
            'one': {
                'char': 'a',
                'commented': {
                    'item': '# a',
                },
                'real': {
                    'one': {
                        'comment': 'a\n#b',
                    },
                },
            },
            'longer': {
                'char': 'ab',
            },
            'two': {
                'same': {
                    'line': 'a b',
                },
                'diff': {
                    'lines': 'a\nb',
                },
                'commented': {
                    'same': {
                        'line': '# a b',
                    },
                },
            },
        })

    def tearDown(self):
        self._patcher.reset()

    def test_one_char_item(self):
        assert({'a'} == bde_items('one', 'char'))

    def test_longer_char_item(self):
        assert({'ab'} == bde_items('longer', 'char'))

    def test_two_items_on_same_line(self):
        assert({'a', 'b'} == bde_items('two', 'same', 'line'))

    def test_item_on_each_line(self):
        assert({'a', 'b'} == bde_items('two', 'diff', 'lines'))

    def test_one_commented_item(self):
        assert(set() == bde_items('one', 'commented', 'item'))

    def test_two_commented_items_same_line(self):
        assert(set() == bde_items('two', 'commented', 'same', 'line'))

    def test_one_real_one_comment(self):
        assert({'a'} == bde_items('one', 'real', 'one', 'comment'))

class ResolveTest(TestCase):
    class MockResolver(object):
        def __init__(self, adjacencies):
            self._adjacencies = adjacencies
            self._resolutions = []

        def dependencies(self, name):
            return self._adjacencies[name]

        def resolve(self, name, store):
            self._resolutions.append(name)
            return name

        def resolutions(self):
            return self._resolutions

    def test_no_resolution(self):
        r  = self.MockResolver({})
        ns = resolve(r, [])
        assert([] == ns)
        assert([] == r.resolutions())

    def test_one_resolution_zero_deps(self):
        r  = self.MockResolver({'a': []})
        ns = resolve(r, ['a'])
        assert(['a'] == ns)
        assert(['a'] == r.resolutions())

    def test_caches_resolve(self):
        r  = self.MockResolver({'a': ['b'],
                                'b': [],    })
        ns = resolve(r, ['a'])
        assert(['a', 'b'] == ns)
        assert(2 == len(r.resolutions()))
        assert('a' in r.resolutions())
        assert('b' in r.resolutions())

        r  = self.MockResolver({'a': ['b'],
                                'b': [],    })
        ns = resolve(r, ['a', 'b'])
        assert(['a', 'b'] == ns)
        assert(2 == len(r.resolutions()))
        assert('a' in r.resolutions())
        assert('b' in r.resolutions())

class PackageResolverTest(TestCase):
    def setUp(self):
        self.roots = [
            'r',
        ]
        self._patcher = OsPatcher([bdemeta.resolver], {
            'r': {
                'g1': {
                    'g1p1': {
                        'package': {
                            'g1p1.dep': '',
                            'g1p1.mem': '',
                        },
                    },
                    'g1p2': {
                        'package': {
                            'g1p2.dep': '',
                            'g1p2.mem': 'g1p2_c1',
                        },
                    },
                    'g1p3': {
                        'package': {
                            'g1p3.dep': '',
                            'g1p3.mem': 'g1p3_c1',
                        },
                        'g1p3_c1.t.cpp': '',
                    },
                    'g1+p4': {
                        'package': {
                            'g1+p4.dep': '',
                            'g1+p4.mem': '',
                        },
                        'a.cpp': '',
                        'b.cpp': '',
                    },
                    'g1+p5': {
                        'package': {
                            'g1+p5.dep': '',
                            'g1+p5.mem': '',
                        },
                        'a.c': '',
                    },
                    'g1+p6': {
                        'package': {
                            'g1+p6.dep': '',
                            'g1+p6.mem': '',
                        },
                        'a.x': '',
                    },
                },
                'g2': {
                    'g2p1': {
                        'package': {
                            'g2p1.dep': '',
                            'g2p1.mem': '',
                        },
                    },
                    'g2p2': {
                        'package': {
                            'g2p2.dep': 'g2p1',
                            'g2p2.mem': '',
                        },
                    },
                },
            },
        })

    def tearDown(self):
        self._patcher.reset()

    def test_empty_dependencies(self):
        r = PackageResolver(pjoin('r', 'g1'))
        assert(set() == r.dependencies('g1p1'))

    def test_non_empty_dependencies(self):
        r = PackageResolver(pjoin('r', 'g2'))
        assert(set(['g2p1']) == r.dependencies('g2p2'))

    def test_empty_package(self):
        r = PackageResolver(pjoin('r', 'g1'))
        p = r.resolve('g1p1', {})
        assert('g1p1'                     == p)
        assert([]                         == p.dependencies())
        assert([pjoin('r', 'g1', 'g1p1')] == list(p.includes()))
        assert([]                         == list(p.sources()))

    def test_one_non_driver_component(self):
        r = PackageResolver(pjoin('r', 'g1'))
        p = r.resolve('g1p2', {})
        assert('g1p2'                     == p)
        assert([]                         == p.dependencies())
        assert([pjoin('r', 'g1', 'g1p2')] == list(p.includes()))
        assert([pjoin('r', 'g1', 'g1p2', 'g1p2_c1.cpp')]
                                          == list(p.sources()))
        assert(0                          == len(list(p.drivers())))

    def test_one_driver_component(self):
        r = PackageResolver(pjoin('r', 'g1'))
        p = r.resolve('g1p3', {})
        assert('g1p3'                     == p)
        assert([]                         == p.dependencies())
        assert([pjoin('r', 'g1', 'g1p3')] == list(p.includes()))
        assert([pjoin('r', 'g1', 'g1p3', 'g1p3_c1.h')]
                                          == list(p.headers()))
        assert([pjoin('r', 'g1', 'g1p3', 'g1p3_c1.cpp')]
                                          == list(p.sources()))
        assert([pjoin('r', 'g1', 'g1p3', 'g1p3_c1.t.cpp')]
                                          == list(p.drivers()))

    def test_empty_package_with_dependency(self):
        r = PackageResolver(pjoin('r', 'g2'))
        p1 = r.resolve('g2p1', {})
        assert('g2p1' == p1)
        assert([]     == p1.dependencies())
        p2 = r.resolve('g2p2', { 'g2p1': p1 })
        assert('g2p2' == p2)
        assert([p1]   == p2.dependencies())

    def test_thirdparty_package_lists_cpps(self):
        r = PackageResolver(pjoin('r', 'g1'))
        p = r.resolve('g1+p4', {})
        assert('g1+p4'                     == p)
        assert([]                          == p.dependencies())
        assert([pjoin('r', 'g1', 'g1+p4')] == list(p.includes()))
        assert(2                           == len(list(p.sources())))
        assert(pjoin('r', 'g1', 'g1+p4', 'a.cpp') in list(p.sources()))
        assert(pjoin('r', 'g1', 'g1+p4', 'b.cpp') in list(p.sources()))

    def test_thirdparty_package_lists_cs(self):
        r = PackageResolver(pjoin('r', 'g1'))
        p = r.resolve('g1+p5', {})
        assert('g1+p5'                     == p)
        assert([]                          == p.dependencies())
        assert([pjoin('r', 'g1', 'g1+p5')] == list(p.includes()))
        assert(1                           == len(list(p.sources())))
        assert(pjoin('r', 'g1', 'g1+p5', 'a.c') in list(p.sources()))

    def test_thirdparty_package_ignores_non_c_non_cpp(self):
        r = PackageResolver(pjoin('r', 'g1'))
        p = r.resolve('g1+p6', {})
        assert('g1+p6'                     == p)
        assert([]                          == p.dependencies())
        assert([pjoin('r', 'g1', 'g1+p6')] == list(p.includes()))
        assert(0                           == len(list(p.sources())))

    def test_level_two_package_has_dependency(self):
        r = PackageResolver(pjoin('r', 'g2'))

        p1 = r.resolve('g2p1', {})
        assert('g2p1'                     == p1)
        assert([]                         == p1.dependencies())
        assert([pjoin('r', 'g2', 'g2p1')] == list(p1.includes()))
        assert(0                          == len(list(p1.sources())))

        p2 = r.resolve('g2p2', { 'g2p1': p1 })
        assert('g2p2'                     == p2)
        assert([p1]                       == p2.dependencies())
        assert([pjoin('r', 'g2', 'g2p2')] == list(p2.includes()))
        assert(0                          == len(list(p2.sources())))

class UnitResolverTest(TestCase):
    def setUp(self):
        self.roots = [
            'r',
        ]
        self._patcher = OsPatcher([bdemeta.resolver], {
            'r': {
                'groups': {
                    'gr1': {
                        'group': {
                            'gr1.dep': '',
                            'gr1.mem': 'gr1p1 gr1p2',
                        },
                        'gr1p1': {
                            'package': {
                                'gr1p1.dep': '',
                            },
                        },
                        'gr1p2': {
                            'package': {
                                'gr1p2.dep': '',
                            },
                        },
                    },
                    'gr2': {
                        'group': {
                            'gr2.dep': 'gr1',
                        },
                    },
                },
            },
        })

    def tearDown(self):
        self._patcher.reset()

    def test_group_identification(self):
        r = UnitResolver(self.roots)
        assert({
            'type': 'group',
            'path': pjoin('r', 'groups', 'gr1')
        } == r.identify('gr1'))

    def test_group_with_one_dependency(self):
        r = UnitResolver(self.roots)
        assert(set(['gr1']) == r.dependencies('gr2'))

    def test_level_one_group_resolution(self):
        r = UnitResolver(self.roots)

        gr1 = r.resolve('gr1', {})
        assert('gr1' == gr1)

    def test_level_one_group_resolution_packages(self):
        ur = UnitResolver(self.roots)
        pr = PackageResolver(pjoin('r', 'groups', 'gr1'))

        gr1 = ur.resolve('gr1', {})
        assert('gr1' == gr1)
        assert(resolve(pr, ['gr1p1', 'gr1p2']) == gr1._packages)

    def test_level_two_group_resolution(self):
        r = UnitResolver(self.roots)

        gr1 = r.resolve('gr1', {})
        gr2 = r.resolve('gr2', { 'gr1': gr1 })
        assert('gr2' == gr2)

class StandaloneResolverTest(TestCase):
    def setUp(self):
        self.roots = [
            'r',
        ]
        self._patcher = OsPatcher([bdemeta.resolver], {
            'r': {
                'adapters': {
                    'p1': {
                        'package': {
                            'p1.dep': '',
                            'p1.mem': 'p1c1 p1c2',
                        },
                    },
                    'p2': {
                        'package': {
                            'p2.dep': 'p1',
                        },
                    },
                },
            },
        })

    def tearDown(self):
        self._patcher.reset()

    def test_adapter_identification(self):
        r = UnitResolver(self.roots)
        assert({
            'type': 'package',
            'path': pjoin('r', 'adapters', 'p1')
        } == r.identify('p1'))

    def test_standalone_with_one_dependency(self):
        r = UnitResolver(self.roots)
        assert(set(['p1']) == r.dependencies('p2'))

    def test_level_one_standalone_resolution(self):
        r = UnitResolver(self.roots)

        p1 = r.resolve('p1', {})
        assert('p1' == p1)

    def test_level_one_standalone_resolution_components(self):
        r = UnitResolver(self.roots)

        p1 = r.resolve('p1', {})
        assert('p1' == p1)

        c1 = pjoin('r', 'adapters', 'p1', 'p1c1.cpp')
        c2 = pjoin('r', 'adapters', 'p1', 'p1c2.cpp')
        assert([c1, c2] == list(sorted(p1.sources())))

    def test_level_two_group_resolution(self):
        r = UnitResolver(self.roots)

        p1 = r.resolve('p1', {})
        assert('p1' == p1)

        p2 = r.resolve('p2', { 'p1': p1 })
        assert('p2' == p2)

class CMakeResolverTest(TestCase):
    def setUp(self):
        self.roots = [
            'r',
        ]
        self._patcher = OsPatcher([bdemeta.resolver], {
            'r': {
                'thirdparty': {
                    't1': {
                        'CMakeLists.txt': '',
                    },
                },
            },
        })

    def tearDown(self):
        self._patcher.reset()

    def test_cmake_identification(self):
        r = UnitResolver(self.roots)
        assert({
            'type': 'cmake',
            'path': pjoin('r', 'thirdparty', 't1')
        } == r.identify('t1'))

    def test_cmake_path(self):
        r = UnitResolver(self.roots)
        t = r.resolve('t1', {})
        assert(pjoin('r', 'thirdparty', 't1') == t.path())

class NotFoundErrorsTest(TestCase):
    def setUp(self):
        self.roots = [
            'r',
        ]
        self._patcher = OsPatcher([bdemeta.resolver], {
            'r': { },
        })

    def tearDown(self):
        self._patcher.reset()

    def test_non_identification(self):
        r = UnitResolver(self.roots)
        caught = False
        try:
            r.identify('foo')
        except bdemeta.resolver.TargetNotFoundError:
            caught = True
        assert(caught)

