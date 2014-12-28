# tests.test_bdemeta

from collections import defaultdict
from io          import StringIO
from itertools   import chain
from unittest    import TestCase

from bdemeta          import parse_config, InvalidArgumentsError, run, ninja
from bdemeta.resolver import resolve, UnitResolver
from tests.patcher    import OsPatcher

import bdemeta

class ParseConfigTest(TestCase):
    def setUp(self):
        self._patcher = OsPatcher(bdemeta, {
            u'foo': u'{"baz": 9}',
        })

    def tearDown(self):
        self._patcher.reset()

    def test_empty_config_for_nonexistent_file(self):
        assert({} == parse_config('bar'))

    def test_parses_file(self):
        assert({ 'baz': 9 } == parse_config(u'foo'))

class InvalidArgumentsErrorTest(TestCase):
    def test_carries_one_attribute(self):
        e = InvalidArgumentsError('foo')
        assert('foo' == e.message)

class RunTest(TestCase):
    def setUp(self):
        self._config = {
            'roots': ['r'],
            'units': defaultdict(lambda: dict((('internal_cflags', []),
                                               ('external_cflags', []),
                                               ('ld_args',         []),
                                               ('deps',            [])))),
        }
        self._patcher = OsPatcher(bdemeta, {
            u'foo': u'{"baz": 9}',
            u'.bdemetarc': u'{"roots":["r"]}',
            u'r': {
                u'applications': {
                    u'm_app': {
                        u'application': {
                            'm_app.dep': u'gr2',
                        },
                    },
                },
                u'groups': {
                    u'gr1': {
                        u'group': {
                            'gr1.dep': u'',
                            'gr1.mem': u'gr1p1 gr1p2',
                        },
                        u'gr1p1': {
                            u'package': {
                                'gr1p1.dep': u'',
                            },
                        },
                        u'gr1p2': {
                            u'package': {
                                'gr1p2.dep': u'',
                            },
                        },
                    },
                    u'gr2': {
                        u'group': {
                            'gr2.dep': u'gr1',
                        },
                    },
                },
            },
        })

    def tearDown(self):
        self._patcher.reset()

    def test_no_mode_error(self):
        message = None
        try:
            run(StringIO(), [])
        except InvalidArgumentsError as e:
            message = e.message
        assert('No mode specified' == message)

    def test_unknown_mode_error(self):
        message = None
        try:
            run(StringIO(), ['foo'])
        except InvalidArgumentsError as e:
            message = e.message
        assert('Unknown mode \'{}\''.format('foo') == message)

    def test_walk_one_target(self):
        f = StringIO()
        run(f, ['walk', 'foo'])

        r  = UnitResolver(self._config)
        us = resolve(r, ['foo'])
        ts = [t for t in us if isinstance(t, bdemeta.types.Target)]

        assert(u' '.join(ts) + u'\n' == f.getvalue())

    def test_target_with_dependencies(self):
        f = StringIO()
        run(f, ['walk', 'gr2'])

        r  = UnitResolver(self._config)
        us = resolve(r, ['gr2'])
        ts = [t for t in us if isinstance(t, bdemeta.types.Target)]

        assert(u' '.join(ts) + u'\n' == f.getvalue())

    def test_cflags(self):
        f = StringIO()
        run(f, ['cflags', 'gr2'])

        r      = UnitResolver(self._config)
        us     = resolve(r, ['gr2'])
        cflags = u' '.join(chain(*[u.cflags() for u in us]))

        assert(cflags + u'\n' == f.getvalue())

    def test_ninja_no_toolchain(self):
        f1 = StringIO()
        run(f1, ['ninja', 'gr2'])

        r  = UnitResolver(self._config)
        us = resolve(r, ['gr2'])
        ts = [t for t in us if isinstance(t, bdemeta.types.Target)]
        f2 = StringIO()
        ninja.generate(ts, { 'cc':  'cc',
                             'c++': 'c++',
                             'ar':  'ar', }, f2)

        assert(f1.getvalue() == f2.getvalue())

