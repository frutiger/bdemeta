from bdemeta.functional import memoize

@memoize
def traverse(ns):
    result = frozenset(ns)
    for n in ns:
        result = result.union(traverse(n.dependencies()))
    return result

@memoize
def tsort(nodes):
    tsorted = []
    marks   = {}

    def visit(node):
        if node.name() not in marks:
            marks[node.name()] = 'working'
            for child in node.dependencies():
                visit(child)
            marks[node.name()] = 'done'
            tsorted.insert(0, node)
        elif marks[node.name()] == 'done':
            return
        else:
            raise RuntimeError('cyclic graph')

    [visit(n) for n in nodes]
    return tsorted

