# tests.test_bdemeta

from unittest import TestCase

from bdemeta       import parse_config
from tests.patcher import IoPatcher

import bdemeta

class ParseConfigTest(TestCase):
    def setUp(self):
        self._patcher = IoPatcher(bdemeta, {
            u'foo': u'{"baz": 9}',
        })

    def tearDown(self):
        self._patcher.reset()

    def test_empty_config_for_nonexistent_file(self):
        assert({} == parse_config('bar'))

    def test_parses_file(self):
        assert({ 'baz': 9 } == parse_config(u'foo'))

