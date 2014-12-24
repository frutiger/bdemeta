# tests.test_resolver

from unittest import TestCase

from bdemeta.resolver import bde_items
from tests.patcher    import OsPatcher

import bdemeta.resolver

class BdeItemsTest(TestCase):
    def setUp(self):
        self._patcher = OsPatcher(bdemeta.resolver, {
            'one': {
                'char': u'a',
                'commented': {
                    'item': u'# a',
                },
                'real': {
                    'one': {
                        'comment': u'a\n#b',
                    },
                },
            },
            'longer': {
                'char': u'ab',
            },
            'two': {
                'same': {
                    'line': u'a b',
                },
                'diff': {
                    'lines': u'a\nb',
                },
                'commented': {
                    'same': {
                        'line': u'# a b',
                    },
                },
            },
        })

    def tearDown(self):
        self._patcher.reset()

    def test_one_char_item(self):
        assert(['a'] == bde_items('one', 'char'))

    def test_longer_char_item(self):
        assert(['ab'] == bde_items('longer', 'char'))

    def test_two_items_on_same_line(self):
        assert(['a', 'b'] == bde_items('two', 'same', 'line'))

    def test_item_on_each_line(self):
        assert(['a', 'b'] == bde_items('two', 'diff', 'lines'))

    def test_one_commented_item(self):
        assert([] == bde_items('one', 'commented', 'item'))

    def test_two_commented_items_same_line(self):
        assert([] == bde_items('two', 'commented', 'same', 'line'))

    def test_one_real_one_comment(self):
        assert(['a'] == bde_items('one', 'real', 'one', 'comment'))

