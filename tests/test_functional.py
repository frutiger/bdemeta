# tests.test_functional

from unittest import TestCase

from bdemeta.functional import memoize

class ResultCachingTest(TestCase):
    def setUp(self):
        self.num_runs = 0

    def test(self):
        @memoize
        def add_one(x):
            self.num_runs = self.num_runs + 1
            return x + 1

        assert(self.num_runs == 0)
        add_one(2);
        assert(self.num_runs == 1)
        add_one(2);
        assert(self.num_runs == 1)

class CachedResultsAreCopiedTest(TestCase):
    def test(self):
        @memoize
        def empty_array():
            return []

        result1 = empty_array()
        result1.append(0)
        assert(len(result1) == 1)
        result2 = empty_array()
        assert(len(result2) == 0)

