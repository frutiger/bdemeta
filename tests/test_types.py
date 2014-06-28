from unittest import TestCase

from bdemeta.types import Unit, Package, Group

def dict_resolver(resolutions):
    return lambda name: resolutions[name]

class TestUnit(TestCase):
    def test_equality(self):
        a1 = Unit(None, 'a', None, None)
        a2 = Unit(None, 'a', None, None)
        b1 = Unit(None, 'b', None, None)
        b2 = Unit(None, 'b', None, None)

        assert(a1 == a2)
        assert(a1 != b1)
        assert(a1 != b2)

        assert(a2 != b1)
        assert(a2 != b2)
        assert(a2 == a1)

        assert(b1 == b2)
        assert(b1 != a1)
        assert(b1 != a2)

        assert(b2 != a1)
        assert(b2 != a2)
        assert(b2 == b1)

    def test_hash(self):
        a1 = Unit(None, 'a', None, None)
        a2 = Unit(None, 'a', None, None)
        b1 = Unit(None, 'b', None, None)
        b2 = Unit(None, 'b', None, None)

        assert(hash(a1) == hash(a2))
        assert(hash(a1) != hash(b1))
        assert(hash(a1) != hash(b2))

        assert(hash(a2) != hash(b1))
        assert(hash(a2) != hash(b2))
        assert(hash(a2) == hash(a1))

        assert(hash(b1) == hash(b2))
        assert(hash(b1) != hash(a1))
        assert(hash(b1) != hash(a2))

        assert(hash(b2) != hash(a1))
        assert(hash(b2) != hash(a2))
        assert(hash(b2) == hash(b1))

    def test_name(self):
        u = Unit(None, 'a', None, None)
        assert(u.name() == 'a')

    def test_flags(self):
        u = Unit(None, None, None, { 'a': 5 })
        assert(u.flags('a') == 5)

    def test_dependencies(self):
        resolver = dict_resolver({ 'b': 5 })
        u = Unit(resolver, None, ('b'), None)
        dependencies = u.dependencies()
        assert(len(dependencies) == 1)
        assert(5 in dependencies)
