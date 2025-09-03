import networkx as nx

from typing import List, Iterable, Optional, Set, Tuple, Any

from functools import cmp_to_key
import heapq as hq


def find_shortest_path(
    graph: nx.DiGraph,
    origin,
    destination,
    intermediate: Optional[Any] = None,
    weight: str = "weight",
    namespace: str = "module",
):

    if intermediate is not None:

        path_1 = find_shortest_path(
            graph, origin, intermediate, weight=weight, namespace=namespace
        )

        path_2 = find_shortest_path(
            graph, intermediate, destination, weight=weight, namespace=namespace
        )

        return path_1 + path_2[1:]

    if origin not in graph.nodes or destination not in graph.nodes:
        raise nx.exception.NodeNotFound()

    distances = {}
    predecessors = {}

    def __sort_fn(a, b):
        return (a[0] > b[0]) - (a[0] < b[0])

    key_fn = cmp_to_key(__sort_fn)  # type: ignore
    heap = [key_fn((0, origin, None))]

    hq.heapify(heap)

    while heap:
        dist, node, predecessor = hq.heappop(heap).obj  # type: ignore
 
        if node in distances:
            continue  # Already encountered before

        distances[node] = dist
        predecessors[node] = predecessor

        for neighbor in graph.neighbors(node):
            if neighbor in distances:
                continue

            cost: int = graph.get_edge_data(node, neighbor)[weight]
            print(f"-{neighbor}, {dist+cost}")

            hq.heappush(heap, key_fn((dist + cost, neighbor, node)))

        if node == destination:
            break

    if destination not in predecessors.keys():
        raise nx.NetworkXNoPath
    # Backtrack path
    def _find_path(path: List):
        node = path[0]
        if node == origin:
            return path
        else:
            return _find_path([predecessors[node]] + path)

    return _find_path(path=[destination])
