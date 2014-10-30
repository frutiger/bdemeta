# tests.test_graph

import itertools
from unittest    import TestCase
from collections import defaultdict

from bdemeta.graph import traverse, tsort

def make_graph(nodes, edges):
    class Node(object):
        def __init__(self, name):
            self._name = name

        def name(self):
            return self._name

        def dependencies(self):
            return tuple([result[edge[1]] for edge in edges if edge[0] == self._name])

        def __repr__(self):
            return '{} -> {}'.format(self._name,
                                     ','.join([d._name for d in self.dependencies()]))

    result = {node: Node(node) for node in nodes}
    return [result[node] for node in nodes]

class TraverseTest(TestCase):
    def test_zero_nodes(self):
        assert(len(traverse(())) == 0)

    def test_one_node(self):
        a = make_graph(['a'], [])[0]
        nodes = traverse(frozenset((a,)))

        assert(len(nodes) == 1)
        assert(a in nodes)

    def test_two_disconnected_nodes(self):
        a, b = make_graph(['a', 'b'], [])

        nodes = traverse(frozenset((a,)))
        assert(len(nodes) == 1)
        assert(a in nodes)

        nodes = traverse(frozenset((b,)))
        assert(len(nodes) == 1)
        assert(b in nodes)

    def test_two_linear_nodes(self):
        a, b = make_graph(['a', 'b'], [['a', 'b']])

        nodes = traverse(frozenset((a,)))
        assert(len(nodes) == 2)
        assert(a in nodes)
        assert(b in nodes)

        nodes = traverse(frozenset((b,)))
        assert(len(nodes) == 1)
        assert(b in nodes)

    def test_three_linear_nodes(self):
        a, b, c = make_graph(['a', 'b', 'c'],
                             [['a', 'b'],
                              ['b', 'c']])

        nodes = traverse(frozenset((a,)))
        assert(len(nodes) == 3)
        assert(a in nodes)
        assert(b in nodes)
        assert(c in nodes)

        nodes = traverse(frozenset((b,)))
        assert(len(nodes) == 2)
        assert(b in nodes)
        assert(c in nodes)

        nodes = traverse(frozenset((c,)))
        assert(len(nodes) == 1)
        assert(c in nodes)

    def test_three_nodes_two_edges(self):
        a, b, c = make_graph(['a', 'b', 'c'],
                             [['a', 'b'],
                              ['a', 'c']])

        nodes = traverse(frozenset((a,)))
        assert(len(nodes) == 3)
        assert(a in nodes)
        assert(c in nodes)
        assert(c in nodes)

        nodes = traverse(frozenset((b,)))
        assert(len(nodes) == 1)
        assert(b in nodes)

        nodes = traverse(frozenset((c,)))
        assert(len(nodes) == 1)

class TsortTest(TestCase):
    def test_identity_for_zero_nodes(self):
        assert(len(tsort(())) == 0)

    def test_identity_for_one_node(self):
        #  a    =>    a
        a = make_graph(['a'], [])[0]
        nodes = traverse(frozenset((a,)))
        nodes = tsort(nodes)

        assert(len(nodes) == 1)
        assert(a in nodes)

    def test_two_linear_nodes(self):
        #  a
        #  |    =>    a, b
        #  b
        a, b = make_graph(['a', 'b'], [['a', 'b']])

        for permutation in itertools.permutations([a, b]):
            nodes = tsort(frozenset(permutation))
            assert(len(nodes) == 2)
            assert(nodes[0] == a)
            assert(nodes[1] == b)

    def test_three_linear_nodes(self):
        #  a
        #  |
        #  b    =>    a, b, c
        #  |
        #  c
        a, b, c = make_graph(['a', 'b', 'c'],
                             [['a', 'b'],
                              ['b', 'c']])

        for permutation in itertools.permutations([a, b, c]):
            nodes = tsort(frozenset(permutation))
            assert(len(nodes) == 3)
            assert(nodes[0] == a)
            assert(nodes[1] == b)
            assert(nodes[2] == c)

    def test_three_nodes_two_edges(self):
        #    a
        #   / \     =>    a, b, c
        #  b   c
        a, b, c = make_graph(['a', 'b', 'c'],
                             [['a', 'b'],
                              ['a', 'c']])

        for permutation in itertools.permutations([a, b, c]):
            nodes = tsort(frozenset(permutation))
            assert(len(nodes) == 3)
            assert(nodes[0] == a)
            assert(nodes[1] == b)
            assert(nodes[2] == c)

    def test_four_nodes_diamond(self):
        #    a
        #   / \
        #  b   c    =>    a, b, c, d
        #   \ /
        #    d
        a, b, c, d = make_graph(['a', 'b', 'c', 'd'],
                                [['a', 'b'],
                                 ['a', 'c'],
                                 ['b', 'd'],
                                 ['c', 'd']])

        for permutation in itertools.permutations([a, b, c, d]):
            nodes = tsort(frozenset(permutation))
            assert(len(nodes) == 4)
            assert(nodes[0] == a)
            assert(nodes[1] == b)
            assert(nodes[2] == c)
            assert(nodes[3] == d)

    def test_six_nodes_two_graphs(self):
        #       c
        #      / \
        #  a  |   d    =>    c, a, d, b, e, f
        #  |  |   |
        #  b  e   f
        a, b, c, d, e, f = make_graph(['a', 'b', 'c', 'd', 'e', 'f'],
                                      [['a', 'b'],
                                       ['c', 'd'],
                                       ['c', 'e'],
                                       ['d', 'f']])

        for permutation in itertools.permutations([a, b, c, d, e, f]):
            nodes = tsort(frozenset(permutation))
            assert(len(nodes) == 6)
            assert(nodes[0] == c)
            assert(nodes[1] == a)
            assert(nodes[2] == d)
            assert(nodes[3] == b)
            assert(nodes[4] == e)
            assert(nodes[5] == f)

