# bdemeta.graph

from bdemeta.functional import memoize

@memoize
def traverse(ns):
    result = frozenset(ns)
    for n in ns:
        result = result.union(traverse(n.dependencies()))
    return result

@memoize
def tsort(nodes):
    nodeLevels = {}
    levelNodes = {}

    def visit(node):
        if node.name() not in nodeLevels:
            nodeLevels[node.name()] = -1
            level = 0
            for child in node.dependencies():
                level = max(level, visit(child) + 1)
            nodeLevels[node.name()] = level
            if level not in levelNodes:
                levelNodes[level] = []
            levelNodes[level].append(node)
            return level
        elif -1 == nodeLevels[node.name()]:
            raise RuntimeError('cyclic graph')
        else:
            return nodeLevels[node.name()]

    [visit (n) for n in nodes]

    tsorted = []
    for level in levelNodes:
        tsorted[:0] = sorted(levelNodes[level], key=lambda n: n.name())

    return tsorted

