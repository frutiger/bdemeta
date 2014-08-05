from unittest import TestCase

from bdemeta.config import merge

class TestInputsUnchanged(TestCase):
    def test_empty(self):
        empty = {}
        merge(empty, empty)
        assert({} == empty)

    def test_empty_source(self):
        source    = {}
        extension = {'a': 1}
        merge(source, extension)
        assert({}       == source)
        assert({'a': 1} == extension)

    def test_empty_extension(self):
        source    = {'a': 1}
        extension = {}
        merge(source, extension)
        assert({'a': 1} == source)
        assert({}       == extension)

    def test_empty_source_sequence_extension(self):
        source    = {}
        extension = {'a': [1, 2, 3]}
        merge(source, extension)
        assert({}               == source)
        assert({'a': [1, 2, 3]} == extension)

    def test_empty_extension_sequence_source(self):
        source    = {'a': [1, 2, 3]}
        extension = {}
        merge(source, extension)
        assert({'a': [1, 2, 3]} == source)
        assert({}               == extension)

class TestMerge(TestCase):
    def test_simple_values(self):
        assert({} == merge({}, {}))
        assert({'a': 1} == merge({'a': 1}, {}))
        assert({'a': 1} == merge({}, {'a': 1}))

    def test_sequence_values(self):
        assert({'a': [1, 2, 'b']} == merge({'a': [1, 2, 'b']}, {}))
        assert({'a': [1, 2, 'b']} == merge({}, {'a': [1, 2, 'b']}))

        assert({'a': [1, 2, 'b', 3]} == merge({'a': [1, 2, 'b']}, {'a': [3]}))
        assert({'a': [3, 1, 2, 'b']} == merge({'a': [3]}, {'a': [1, 2, 'b']}))

    def test_dict_values(self):
        assert({'a': {'b': 42}} == merge({'a': {'b': 42}}, {}))
        assert({'a': {'b': 42}} == merge({}, {'a': {'b': 42}}))

        assert({'a': {'b': 42, 'c': -42}} == merge({'a': {'b':  42}},
                                                   {'a': {'c': -42}}))
        assert({'a': {'b': 42, 'c': -42}} == merge({'a': {'c': -42}},
                                                   {'a': {'b':  42}}))

