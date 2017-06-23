# tests.test_bdemeta

from io       import StringIO
from pathlib  import Path as P
from unittest import TestCase

from bdemeta.__main__ import parse_config, InvalidArgumentsError, run
from bdemeta.resolver import resolve, UnitResolver
from tests.patcher    import OsPatcher

import bdemeta

class ParseConfigTest(TestCase):
    def setUp(self):
        self._patcher = OsPatcher({
            'foo': '{"baz": 9}',
        })

    def tearDown(self):
        self._patcher.reset()

    def test_empty_config_for_nonexistent_file(self):
        assert([] == parse_config(P('bar')))

    def test_parses_file(self):
        assert({ 'baz': 9 } == parse_config(P('foo')))

class InvalidArgumentsErrorTest(TestCase):
    def test_carries_one_attribute(self):
        e = InvalidArgumentsError('foo')
        assert('foo' == e.args[0])

class RunTest(TestCase):
    def setUp(self):
        self._config = [
            P('r'),
        ]
        self._patcher = OsPatcher({
            '.bderoots.conf': '["r"]',
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

    def test_no_mode_error(self):
        message = None
        try:
            run(StringIO(), [])
        except InvalidArgumentsError as e:
            message = e.args[0]
        assert('No mode specified' == message)

    def test_unknown_mode_error(self):
        message = None
        try:
            run(StringIO(), ['foo'])
        except InvalidArgumentsError as e:
            message = e.args[0]
        assert('Unknown mode \'{}\''.format('foo') == message)

    def test_target_with_dependencies(self):
        f = StringIO()
        run(f, ['walk', 'gr2'])

        r  = UnitResolver(self._config)
        us = resolve(r, ['gr2'])

        assert(' '.join(us) + '\n' == f.getvalue())

