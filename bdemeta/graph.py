# bdemeta.graph

from typing import List, Callable, Set, Iterable

class CyclicGraphError(RuntimeError):
    def __init__(self, cycle: Iterable[str]) -> None:
        self.cycle = cycle

def tsort(nodes: Iterable[str],
          adjacencies: Callable[[str], Iterable[str]],
          normalize: Callable[[Iterable[str]], Iterable[str]]=lambda x: x) -> List[str]:
    visited: Set[str]    = set()
    postorder: List[str] = []

    def dft(node: str, stack: List[str]) -> None:
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

