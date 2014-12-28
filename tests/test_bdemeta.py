# tests.test_bdemeta

from unittest import TestCase

from bdemeta       import parse_config, InvalidArgumentsError
from tests.patcher import OsPatcher

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

