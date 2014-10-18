# bdemeta.graph

class CyclicGraphError(RuntimeError):
    def __init__(self, cycle):
        self.cycle = cycle

def tsort(nodes, adjacencies, normalize=lambda x: x):
    visited   = set()
    postorder = []

    def dft(node, stack):
        if node in visited:
            return

        if node in stack:
            raise CyclicGraphError(list(stack) + [node])

        stack.append(node)
        for adjacent in normalize(adjacencies(node)):
            dft(adjacent, stack)
        stack.pop()

        visited.add(node)
        postorder.insert(0, node)

    for node in normalize(nodes):
        dft(node, [])

    return postorder

