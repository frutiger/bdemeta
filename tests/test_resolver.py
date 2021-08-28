# tests.test_resolver

from pathlib  import Path as P
from unittest import TestCase

from bdemeta.resolver import bde_items, resolve, PackageResolver, TargetResolver
from bdemeta.resolver import TargetNotFoundError
from bdemeta.types    import Identification
from tests.patcher    import OsPatcher

class BdeItemsTest(TestCase):
    def setUp(self):
        self._patcher = OsPatcher({
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
        assert({'a'} == bde_items(P('one')/'char'))

    def test_longer_char_item(self):
        assert({'ab'} == bde_items(P('longer')/'char'))

    def test_two_items_on_same_line(self):
        assert({'a', 'b'} == bde_items(P('two')/'same'/'line'))

    def test_item_on_each_line(self):
        assert({'a', 'b'} == bde_items(P('two')/'diff'/'lines'))

    def test_one_commented_item(self):
        assert(set() == bde_items(P('one')/'commented'/'item'))

    def test_two_commented_items_same_line(self):
        assert(set() == bde_items(P('two')/'commented'/'same'/'line'))

    def test_one_real_one_comment(self):
        assert({'a'} == bde_items(P('one')/'real'/'one'/'comment'))

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
        self.config = {
            'roots': [
                P('r'),
            ]
        }
        self._patcher = OsPatcher({
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
                        'g1p3_c1.h':     '',
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
                    'g1+p7': {
                        'package': {
                            'g1+p7.dep': '',
                            'g1+p7.mem': '',
                        },
                        'a.h': '',
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
        r = PackageResolver(P('r')/'g1')
        assert(set() == r.dependencies('g1p1'))

    def test_non_empty_dependencies(self):
        r = PackageResolver(P('r')/'g2')
        assert(set(['g2p1']) == r.dependencies('g2p2'))

    def test_empty_package(self):
        r = PackageResolver(P('r')/'g1')
        p = r.resolve('g1p1', {})
        assert('g1p1'                    == p.name)
        assert([]                        == p.dependencies())
        assert([str(P('r')/'g1'/'g1p1')] == list(p.includes()))
        assert([]                        == list(p.sources()))

    def test_one_non_driver_component(self):
        r = PackageResolver(P('r')/'g1')
        p = r.resolve('g1p2', {})
        assert('g1p2'                                  == p.name)
        assert([]                                      == p.dependencies())
        assert([str(P('r')/'g1'/'g1p2')]               == list(p.includes()))
        assert([str(P('r')/'g1'/'g1p2'/'g1p2_c1.cpp')] == list(p.sources()))
        assert([]                                      == list(p.drivers()))

    def test_one_driver_component(self):
        r = PackageResolver(P('r')/'g1')
        p = r.resolve('g1p3', {})
        assert('g1p3'                                    == p.name)
        assert([]                                        == p.dependencies())
        assert([str(P('r')/'g1'/'g1p3')]                 == list(p.includes()))
        assert([str(P('r')/'g1'/'g1p3'/'g1p3_c1.h')]     == list(p.headers()))
        assert([str(P('r')/'g1'/'g1p3'/'g1p3_c1.cpp')]   == list(p.sources()))
        assert([str(P('r')/'g1'/'g1p3'/'g1p3_c1.t.cpp')] == list(p.drivers()))

    def test_empty_package_with_dependency(self):
        r = PackageResolver(P('r')/'g2')

        p1 = r.resolve('g2p1', {})
        assert('g2p1' == p1.name)
        assert([]     == p1.dependencies())

        p2 = r.resolve('g2p2', { 'g2p1': p1 })
        assert('g2p2' == p2.name)
        assert([p1]   == p2.dependencies())

    def test_thirdparty_package_lists_cpps(self):
        r = PackageResolver(P('r')/'g1')
        p = r.resolve('g1+p4', {})

        assert('g1+p4'                    == p.name)
        assert([]                         == p.dependencies())
        assert([str(P('r')/'g1'/'g1+p4')] == list(p.includes()))

        assert(2                                == len(list(p.sources())))
        assert(str(P('r')/'g1'/'g1+p4'/'a.cpp') in list(p.sources()))
        assert(str(P('r')/'g1'/'g1+p4'/'b.cpp') in list(p.sources()))

    def test_thirdparty_package_lists_cs(self):
        r = PackageResolver(P('r')/'g1')
        p = r.resolve('g1+p5', {})
        assert('g1+p5'                          == p.name)
        assert([]                               == p.dependencies())
        assert([str(P('r')/'g1'/'g1+p5')]       == list(p.includes()))
        assert([str(P('r')/'g1'/'g1+p5'/'a.c')] == list(p.sources()))

    def test_thirdparty_package_ignores_non_c_non_cpp(self):
        r = PackageResolver(P('r')/'g1')
        p = r.resolve('g1+p6', {})
        assert('g1+p6'                    == p.name)
        assert([]                         == p.dependencies())
        assert([str(P('r')/'g1'/'g1+p6')] == list(p.includes()))
        assert([]                         == list(p.sources()))

    def test_thirdparty_package_with_header(self):
        r = PackageResolver(P('r')/'g1')
        p = r.resolve('g1+p7', {})
        assert('g1+p7'                          == p.name)
        assert([]                               == p.dependencies())
        assert([str(P('r')/'g1'/'g1+p7')]       == list(p.includes()))
        assert([str(P('r')/'g1'/'g1+p7'/'a.h')] == list(p.headers()))

    def test_level_two_package_has_dependency(self):
        r = PackageResolver(P('r')/'g2')

        p1 = r.resolve('g2p1', {})
        assert('g2p1'                    == p1.name)
        assert([]                        == p1.dependencies())
        assert([str(P('r')/'g2'/'g2p1')] == list(p1.includes()))
        assert(0                         == len(list(p1.sources())))

        p2 = r.resolve('g2p2', { 'g2p1': p1 })
        assert('g2p2'                    == p2.name)
        assert([p1]                      == p2.dependencies())
        assert([str(P('r')/'g2'/'g2p2')] == list(p2.includes()))
        assert([]                        == list(p2.sources()))

class TargetResolverTest(TestCase):
    def setUp(self):
        self.config = {
            'roots': [
                P('r'),
            ]
        }
        self._patcher = OsPatcher({
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
                                'gr1p1.mem': '',
                            },
                        },
                        'gr1p2': {
                            'package': {
                                'gr1p2.dep': '',
                                'gr1p2.mem': '',
                            },
                        },
                    },
                    'gr2': {
                        'group': {
                            'gr2.dep': 'gr1',
                            'gr2.mem': '',
                        },
                    },
                    'gr3': {
                        'group': {
                            'gr3.dep': '',
                            'gr3.t.dep': 'gr1',
                            'gr3.mem': '',
                        },
                    },
                },
            },
        })

    def tearDown(self):
        self._patcher.reset()

    def test_group_identification(self):
        r = TargetResolver(self.config)
        assert(Identification('group', P('r')/'groups'/'gr1') == \
                                                             r.identify('gr1'))

    def test_group_with_one_dependency(self):
        r = TargetResolver(self.config)
        assert(set(['gr1']) == r.dependencies('gr2'))

    def test_group_with_one_dependency_incl_tests_unchanged(self):
        r = TargetResolver(self.config)
        assert(set(['gr1']) == r.dependencies('gr2'))
        r = TargetResolver(self.config, True)
        assert(set(['gr1']) == r.dependencies('gr2'))

    def test_group_with_one_dependency_incl_tests(self):
        r = TargetResolver(self.config)
        assert(set() == r.dependencies('gr3'))
        r = TargetResolver(self.config, True)
        assert(set(['gr1']) == r.dependencies('gr3'))

    def test_level_one_group_resolution(self):
        r = TargetResolver(self.config)

        gr1 = r.resolve('gr1', {})
        assert('gr1' == gr1.name)

    def test_level_one_group_resolution_packages(self):
        ur = TargetResolver(self.config)
        pr = PackageResolver(P('r')/'groups'/'gr1')

        gr1 = ur.resolve('gr1', {})
        assert('gr1' == gr1.name)
        assert([p.name for p in resolve(pr, ['gr1p1', 'gr1p2'])] == \
                                               [p.name for p in gr1._packages])

    def test_level_two_group_resolution(self):
        r = TargetResolver(self.config)

        gr1 = r.resolve('gr1', {})
        gr2 = r.resolve('gr2', { 'gr1': gr1 })
        assert('gr2' == gr2.name)

class ApplicationResolverTest(TestCase):
    def setUp(self):
        self.config = {
            'roots': [
                P('r'),
            ]
        }
        self._patcher = OsPatcher({
            'r': {
                'applications': {
                    'app1': {
                        'package': {
                            'app1.mem': 'app1.m',
                            'app1.dep': 'gr1'
                        },
                        'app1.m.cpp': ''
                    },
                    'app2': {
                        'package': {
                            'app2.mem': '',
                            'app2.dep': 'gr1'
                        },
                        'app2.m.cpp': ''
                    },
                },
                'groups': {
                    'gr1': {
                        'group': {
                            'gr1.dep': '',
                            'gr1.mem': 'gr1p1 gr1p2',
                        },
                        'gr1p1': {
                            'package': {
                                'gr1p1.dep': '',
                                'gr1p1.mem': '',
                            },
                        },
                        'gr1p2': {
                            'package': {
                                'gr1p2.dep': '',
                                'gr1p2.mem': '',
                            },
                        },
                    },
                },
            },
        })

    def tearDown(self):
        self._patcher.reset()

    def test_application_identification(self):
        r = TargetResolver(self.config)
        assert(Identification('application', P('r')/'applications'/'app1') == \
                                                            r.identify('app1'))

    def test_application_with_one_dependency(self):
        r = TargetResolver(self.config)
        assert(set(['gr1']) == r.dependencies('app1'))

    def test_application_resolution_explicit_member(self):
        r = TargetResolver(self.config)

        gr1 = r.resolve('gr1', {})
        app1 = r.resolve('app1', { 'gr1': gr1 })
        assert('app1' == app1.name)
        assert(gr1 in app1.dependencies())
        main_file = P('r')/'applications'/'app1'/'app1.m.cpp'
        assert(str(main_file) in app1.sources())

    def test_application_resolution_implicit_member(self):
        r = TargetResolver(self.config)

        gr1 = r.resolve('gr1', {})
        app2 = r.resolve('app2', { 'gr1': gr1 })
        assert('app2' == app2.name)
        assert(gr1 in app2.dependencies())
        main_file = P('r')/'applications'/'app2'/'app2.m.cpp'
        assert(str(main_file) in app2.sources())

class StandaloneResolverTest(TestCase):
    def setUp(self):
        self.config = {
            'roots': [
                P('r'),
            ],
            'standalones': [
                'adapters',
            ],
        }
        self._patcher = OsPatcher({
            'r': {
                'standalones': {
                    'p1': {
                        'package': {
                            'p1.dep': '',
                            'p1.mem': 'p1c1 p1c2',
                        },
                    },
                    'p2': {
                        'package': {
                            'p2.dep': 'p1',
                            'p2.mem': '',
                        },
                    },
                    'p3': {
                        'package': {
                            'p3.dep': '',
                            'p3.mem': '',
                        },
                        'p3.cmake': '',
                    },
                },
                'adapters': {
                    'p4': {
                        'package': {
                            'p4.dep': '',
                            'p4.mem': 'p4c1 p4c2',
                        },
                    },
                },
            },
        })

    def tearDown(self):
        self._patcher.reset()

    def test_standalone_identification(self):
        r = TargetResolver(self.config)
        assert(Identification('package', P('r')/'standalones'/'p1') == \
                                                              r.identify('p1'))

    def test_custom_standalone_identification(self):
        r = TargetResolver(self.config)
        assert(Identification('package', P('r')/'adapters'/'p4') == \
                                                              r.identify('p4'))

    def test_standalone_with_one_dependency(self):
        r = TargetResolver(self.config)
        assert(set(['p1']) == r.dependencies('p2'))

    def test_level_one_standalone_resolution(self):
        r = TargetResolver(self.config)

        p1 = r.resolve('p1', {})
        assert('p1' == p1.name)

    def test_level_one_standalone_resolution_components(self):
        r = TargetResolver(self.config)

        p1 = r.resolve('p1', {})
        assert('p1' == p1.name)

        c1 = P('r')/'standalones'/'p1'/'p1c1.cpp'
        c2 = P('r')/'standalones'/'p1'/'p1c2.cpp'
        assert([str(c1), str(c2)] == list(sorted(p1.sources())))

    def test_level_two_group_resolution(self):
        r = TargetResolver(self.config)

        p1 = r.resolve('p1', {})
        assert('p1' == p1.name)

        p2 = r.resolve('p2', { 'p1': p1 })
        assert('p2' == p2.name)

    def test_package_cmake_overrides(self):
        r = TargetResolver(self.config)

        p3 = r.resolve('p3', {})
        assert('p3' == p3.name)
        assert(str(P('r')/'standalones'/'p3'/'p3.cmake') == p3.overrides)

class CMakeResolverTest(TestCase):
    def setUp(self):
        self.config = {
            'roots': [
                P('r'),
                P('t2'),
            ]
        }
        self._patcher = OsPatcher({
            'r': {
                'thirdparty': {
                    't1': {
                        'CMakeLists.txt': '',
                    },
                },
            },
            't2': {
                'CMakeLists.txt': '',
            },
        })

    def tearDown(self):
        self._patcher.reset()

    def test_thirdparty_cmake_identification(self):
        r = TargetResolver(self.config)
        assert(Identification('cmake', P('r')/'thirdparty'/'t1') == \
                                                              r.identify('t1'))

    def test_thirdparty_cmake_path(self):
        r = TargetResolver(self.config)
        t = r.resolve('t1', {})
        assert(str(P('r')/'thirdparty'/'t1') == t.path())

    def test_cmake_identification(self):
        r = TargetResolver(self.config)
        assert(Identification('cmake', P('t2')) == r.identify('t2'))

    def test_cmake_path(self):
        r = TargetResolver(self.config)
        t = r.resolve('t2', {})
        assert('t2' == t.path())

class PkgConfigResolverTest(TestCase):
    def setUp(self):
        self.config = {
            'roots': [
                P('r'),
            ],
            'pkg_configs': {
                'foo': 'bar',
            },
        }
        self._patcher = OsPatcher({
        })

    def tearDown(self):
        self._patcher.reset()

    def test_pkg_identification(self):
        r = TargetResolver(self.config)
        assert(Identification('pkg_config', None, 'bar') == r.identify('foo'))

    def test_pkg_name(self):
        r = TargetResolver(self.config)
        t = r.resolve('foo', {})
        assert('bar' == t.package)

class NotFoundErrorsTest(TestCase):
    def setUp(self):
        self.config = {
            'roots': [
                P('r'),
            ]
        }
        self._patcher = OsPatcher({
            'r': { },
        })

    def tearDown(self):
        self._patcher.reset()

    def test_non_identification(self):
        r = TargetResolver(self.config)
        with self.assertRaises(TargetNotFoundError):
            r.identify('foo')

class LazilyBoundTest(TestCase):
    def setUp(self):
        self.config = {
            'roots': [
                P('r'),
            ],
            'providers': {
                'p1': ['bar']
            },
            'runtime_libraries': [
                'bar'
            ]
        }
        self._patcher = OsPatcher({
            'r': {
                'standalones': {
                    'p1': {
                        'package': {
                            'p1.dep': '',
                            'p1.mem': '',
                        },
                    },
                    'p2': {
                        'package': {
                            'p2.dep': 'bar',
                            'p2.mem': '',
                        },
                    }
                },
            }
        })

    def tearDown(self):
        self._patcher.reset()

    def test_lazily_bound_bar(self):
        r   = TargetResolver(self.config)
        p1  = r.resolve('p1',  {})
        bar = r.resolve('bar', { 'p1': p1 })
        p2  = r.resolve('p2',  { 'bar': bar, 'p1': p1 })
        assert(p2.lazily_bound)

class PluginTestsTest(TestCase):
    def setUp(self):
        self.config = {
            'roots': [
                P('r'),
            ],
            'plugin_tests': [
                'gr2'
            ]
        }
        self._patcher = OsPatcher({
            'r': {
                'groups': {
                    'gr1': {
                        'group': {
                            'gr1.dep': '',
                            'gr1.mem': 'gr1p1',
                        },
                        'gr1p1': {
                            'package': {
                                'gr1p1.dep': '',
                                'gr1p1.mem': 'gr1p1_c1',
                            },
                            'gr1p1_c1.cpp': '',
                            'gr1p1_c1.h': '',
                            'gr1p1_c1.t.cpp': '',
                        },
                    },
                    'gr2': {
                        'group': {
                            'gr2.dep': '',
                            'gr2.mem': 'gr2p1',
                        },
                        'gr2p1': {
                            'package': {
                                'gr2p1.dep': '',
                                'gr2p1.mem': 'gr2p1_c1',
                            },
                            'gr2p1_c1.cpp': '',
                            'gr2p1_c1.h': '',
                            'gr2p1_c1.t.cpp': '',
                        },
                    },
                },
            },
        })

    def tearDown(self):
        self._patcher.reset()

    def test_non_plugin_tests(self):
        r   = TargetResolver(self.config)
        gr1 = r.resolve('gr1',  {})
        assert(not gr1.plugin_tests)

    def test_plugin_tests(self):
        r   = TargetResolver(self.config)
        gr2 = r.resolve('gr2',  {})
        assert(gr2.plugin_tests)

