from functools import wraps, partial
import inspect
import networkx as nx
import logging
import time
from collections import namedtuple

from ..func_params import extract_func_params

from typing import (
    Tuple,
    Type,
    Any,
    Generic,
    Callable,
    Union,
    Optional,
    get_origin,
    TYPE_CHECKING,
)

from typing_extensions import TypeVar, get_args

ResolveStep = namedtuple("ResolveStep", ("func", "description"))

Target = TypeVar("Target")
Origin = TypeVar("Origin")
Intermediate = TypeVar("Intermediate", default=Any)


if TYPE_CHECKING:
    Resolve = Union[Target, Intermediate]
else:

    class Resolve(Generic[Target, Intermediate]):
        pass  # Marker Type


def _passthrough(x):
    return x


class Registry:

    def __init__(self) -> None:
        self.graph = nx.DiGraph()

    def add_resolver(
        self, origin: Type[Origin], target: Type[Origin], resolver: Callable
    ):

        if self.graph.has_edge(origin, target):
            return

        def _add_downcasts(subclass: Type):
            for weight, dtype in enumerate(subclass.__mro__):
                if origin == dtype:
                    continue

                self.graph.add_edge(
                    subclass, dtype, resolver=_passthrough, weight=weight
                )

        self.graph.add_edge(origin, target, resolver=resolver, weight=0)

        # Add edges to downcast data
        _add_downcasts(origin)
        _add_downcasts(target)

    def find_resolve_func(
        self,
        origin: Type[Origin],
        target: Type[Target],
        intermediate: Optional[Type[Intermediate]] = None,
    ):
        def _make_step(edge, data):
            u, v = edge
            fn = data["resolver"]

            return ResolveStep(
                fn,
                f"{u.__qualname__} -> {v.__qualname__}: {fn.__qualname__}",
            )

        if origin == target:
            return _passthrough

        # Find the first subclass that is in the graph
        for dtype in origin.__mro__:
            if dtype in self.graph:
                upcast_origin = dtype
                break
        else:
            raise TypeError(
                f"'{origin.__qualname__}' could not be resolved as '{target.__qualname__}'"
            )

        shortest_path = partial(nx.shortest_path, G=self.graph, weight="weight")

        try:
            if intermediate is not None and not origin == intermediate:
                path_to_intermediate = shortest_path(
                    source=upcast_origin, target=intermediate
                )
                path_to_end = shortest_path(source=intermediate, target=target)

                assert isinstance(path_to_intermediate, list)
                assert isinstance(path_to_end, list)

                path = path_to_intermediate + path_to_end[1:]  # type: ignore
            else:
                path = shortest_path(source=upcast_origin, target=target)

        except (nx.NetworkXNoPath, nx.NodeNotFound, StopIteration):
            raise TypeError(
                f"'{origin.__qualname__}' could not be resolved as '{target.__qualname__}'"
            )

        steps = [
            _make_step((u, v), self.graph.get_edge_data(u, v))
            for u, v in zip(path, path[1:])
        ]

        def resolver_fn(value: Origin) -> Target:
            if not isinstance(value, origin):
                raise TypeError("The input value for did not match origin data type")

            x = value
            for step in steps:
                logging.debug(step.description)

                x = step.func(x)  # type: ignore

            if not isinstance(x, target):
                resolve_desc = "\n".join([step.description for step in steps])

                raise TypeError(
                    f"The resolved output with type '{type(x).__qualname__}' did not match target data type '{target.__qualname__}'; this is most likely a bug in a resolver function. Set log level to INFO debug resolver calls.\nResolvers used:\n{resolve_desc}"
                )

            return x

        return resolver_fn

    def resolve(
        self,
        value,
        astype: Type[Target],
        intermediate: Optional[Type[Intermediate]] = None,
    ) -> Target:

        start = time.time()
        resolve_fn = self.find_resolve_func(type(value), astype, intermediate)
        end_search = time.time()

        search_time = end_search - start
        search_time_ms = search_time * 1_000

        resolved = resolve_fn(value)
        end = time.time()

        total = end - start
        total_ms = total * 1_000
        search_percentage = int((search_time / total) * 100)

        logging.info(
            f"Resolving from '{type(value).__qualname__}' to '{astype.__qualname__}' took {total_ms:2f}ms ({search_time_ms:2f}ms ({search_percentage}%) path finding)"
        )

        return resolved

    def _plot_graph(self):  # pragma: no cover
        import networkx as nx
        import matplotlib.pyplot as plt

        G = self.graph

        pos = nx.spring_layout(G, seed=7)
        nx.draw_networkx_nodes(G, pos, node_size=250)
        nx.draw_networkx_edges(G, pos, width=1)

        nx.draw_networkx_labels(G, pos, font_size=12, font_family="sans-serif")

        edge_labels = nx.get_edge_attributes(G, "weight")
        nx.draw_networkx_edge_labels(G, pos, edge_labels)

        ax = plt.gca()
        ax.margins(0.08)
        plt.axis("off")
        plt.tight_layout()
        plt.show()


registry = Registry()


def resolver(f):

    # TODO: Input validation
    in_dtype = f.__annotations__["value"]
    out_dtype = f.__annotations__["return"]

    registry.add_resolver(in_dtype, out_dtype, f)

    return f


def resolve_params(f: Callable):

    signature = inspect.signature(f)

    def _resolve_arg(arg: Tuple[inspect.Parameter, Any]):
        param, value = arg
        if param.annotation is not None and get_origin(param.annotation) == Resolve:
            args = get_args(param.annotation)
            if len(args) == 1:
                args = tuple([args[0], Any])

            target, constraint = args

            constraint = None if constraint == Any else constraint
            value = registry.resolve(value, astype=target, intermediate=constraint)

        return param, value

    @wraps(f)
    def wrapper(*args, **kwargs):
        func_params = extract_func_params(args, kwargs, signature)

        args = list(func_params.items())[: len(args)]
        kwargs = list(func_params.items())[len(args) :]

        args = [_resolve_arg(a) for a in args]
        args = [v for _, v in args]

        kwargs = [_resolve_arg(a) for a in kwargs]
        kwargs = {k.name: v for k, v in kwargs}

        return f(*args, **kwargs)

    return wrapper
