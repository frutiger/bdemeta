from bdemeta.functional import memoize

@memoize
def traverse(ns):
    return frozenset.union(ns, *(traverse(n.dependencies()) for n in ns))

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

