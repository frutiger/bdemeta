# tests.test_graph

from itertools import chain, permutations
from unittest import TestCase

from bdemeta.graph import tsort, CyclicGraphError

adjacencies = lambda x: lambda y: x.get(y, [])

class TsortTest(TestCase):
    def test_one_node(self):
        # a
        graph = adjacencies({ 'a': [], })

        assert(['a'] == tsort(['a'], graph))

    def test_two_disconnected_nodes(self):
        # a  b
        graph = adjacencies({ 'a': [],
                              'b': [], })

        assert(['a'] == tsort(['a'], graph))
        assert(['b'] == tsort(['b'], graph))

    def test_two_linear_nodes(self):
        # a --> b
        graph = adjacencies({ 'a': ['b'], })

        assert(['a', 'b'] == tsort(['a'], graph))
        assert(['b']      == tsort(['b'], graph))

    def test_three_linear_nodes(self):
        # a --> b --> c
        graph = adjacencies({ 'a': ['b'],
                              'b': ['c'], })

        assert(['a', 'b', 'c'] == tsort(['a'], graph))
        assert(['b', 'c'     ] == tsort(['b'], graph))
        assert(['c'          ] == tsort(['c'], graph))

    def test_three_nodes_two_edges(self):
        #  /--> b
        # a
        #  \--> c
        graph = adjacencies({ 'a': ['b', 'c'], })

        postorder = tsort(['a'], graph)
        assert(postorder[0] == 'a')
        assert(postorder[1] == 'b' or postorder[1] == 'c')
        assert(postorder[2] == 'b' or postorder[2] == 'c')

    def test_cycle_raises_error(self):
        #  /--> b
        # |     |
        # a <--/
        graph = adjacencies({ 'a': ['b'],
                              'b': ['a'], })
        cycle = None
        try:
            tsort(['a'], graph)
        except CyclicGraphError as e:
            cycle = e.cycle
        assert(cycle == ['a', 'b', 'a'])

    def test_three_cycle_raises_error(self):
        #  /--> b --> c
        # |           |
        # a <--------/
        graph = adjacencies({ 'a': ['b'],
                              'b': ['c'],
                              'c': ['a'], })
        cycle = None
        try:
            tsort(['a'], graph)
        except CyclicGraphError as e:
            cycle = e.cycle
        assert(cycle == ['a', 'b', 'c', 'a'])

    def test_diamond(self):
        #  /--> b --> d
        # a          ^
        #  \--> c --/
        graph = adjacencies({ 'a': ['b', 'c'],
                              'b': ['d'],
                              'c': ['d'],      })
        postorder = tsort(['a'], graph)
        assert(postorder[0] == 'a')
        assert(postorder[1] == 'b' or postorder[1] == 'c')
        assert(postorder[2] == 'b' or postorder[2] == 'c')
        assert(postorder[3] == 'd')

    def test_normalized_diamond(self):
        #  /--> b --> d
        # a          ^
        #  \--> c --/
        graph = adjacencies({ 'a': ['b', 'c'],
                              'b': ['d'],
                              'c': ['d'],      })
        assert(['a', 'c', 'b', 'd'] == tsort(['a'], graph, sorted))

        graph = adjacencies({ 'a': ['c', 'b'],
                              'b': ['d'],
                              'c': ['d'],      })
        assert(['a', 'c', 'b', 'd'] == tsort(['a'], graph, sorted))

    def test_component_with_two_roots(self):
        # a --> b --> c
        #            ^
        #       d --/
        graph = adjacencies({ 'a': ['b'],
                              'b': ['c'],
                              'd': ['c'], })
        assert(['a', 'b', 'c'] == tsort(['a'], graph))
        assert(['d', 'c']      == tsort(['d'], graph))

        for roots in chain(permutations(['a', 'd']),
                           permutations(['a', 'b', 'd']),
                           permutations(['a', 'b', 'c', 'd'])):
            postorder = tsort(roots, graph)
            assert('a' in postorder)
            assert('b' in postorder)
            assert('c' in postorder)
            assert('d' in postorder)

            assert(postorder[:3] == ['d', 'a', 'b'] or \
                   postorder[:3] == ['a', 'd', 'b'] or \
                   postorder[:3] == ['a', 'b', 'd'])
            assert(postorder[3] == 'c')

    def test_normalized_component_with_two_roots(self):
        # a --> b --> c
        #            ^
        #       d --/
        graph = adjacencies({ 'a': ['b'],
                              'b': ['c'],
                              'd': ['c'],      })
        assert(['a', 'b', 'c'] == tsort(['a'], graph, sorted))
        assert(['d', 'c']      == tsort(['d'], graph, sorted))

        assert(['d', 'a', 'b', 'c'] == tsort(['a', 'd'], graph, sorted))
        assert(['d', 'a', 'b', 'c'] == tsort(['d', 'a'], graph, sorted))

