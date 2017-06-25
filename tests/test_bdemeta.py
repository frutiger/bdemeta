# tests.test_bdemeta

from io       import StringIO
from pathlib  import Path as P
from unittest import TestCase

from bdemeta.__main__ import InvalidArgumentsError, NoConfigError, run
from bdemeta.resolver import resolve, UnitResolver
from tests.patcher    import OsPatcher

import bdemeta

class NoConfigErrorTest(TestCase):
    def setUp(self):
        self._patcher = OsPatcher({})

    def tearDown(self):
        self._patcher.reset()

    def test_no_config_error(self):
        caught = False
        try:
            run(StringIO(), ['walk', 'foo'])
        except NoConfigError as e:
            caught = True
        assert(caught)

class InvalidArgumentsErrorTest(TestCase):
    def test_carries_one_attribute(self):
        e = InvalidArgumentsError('foo')
        assert('foo' == e.args[0])

class RunTest(TestCase):
    def setUp(self):
        self._config = {
            'roots': [
                P('r'),
            ]
        }
        self._patcher = OsPatcher({
            '.bdemeta.conf': '{"roots": ["r"]}',
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

