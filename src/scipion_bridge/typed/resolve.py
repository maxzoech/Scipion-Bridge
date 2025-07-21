from functools import wraps
import inspect
import networkx as nx
import logging
from collections import namedtuple

from ..func_params import extract_func_params

from typing import (
    Tuple,
    Type,
    Any,
    TypeVar,
    Generic,
    Callable,
    Union,
    get_origin,
    get_args,
    TYPE_CHECKING,
)

ResolveStep = namedtuple("ResolveStep", ("func", "description"))
registry = {}

Target = TypeVar("Target")
Origin = TypeVar("Origin")


if TYPE_CHECKING:
    Resolve = Union[Target, Origin]
else:

    class Resolve(Generic[Target, Origin]):
        pass  # Marker Type


def _passthrough(x):
    return x


class Registry:

    def __init__(self) -> None:
        self.graph = nx.DiGraph()

    def add_resolver(
        self, origin: Type[Origin], target: Type[Origin], resolver: Callable
    ):

        self.graph.add_edge(origin, target, resolver=resolver, weight=0)

        # Add edges to downcast data
        for weight, dtype in enumerate(origin.__mro__):
            self.graph.add_edge(origin, dtype, resolver=_passthrough, weight=weight)

    def find_resolve_func(self, origin: Type[Origin], target: Type[Target]):
        def _make_step(edge, data):
            u, v = edge
            return ResolveStep(
                data["resolver"],
                f"{u.__qualname__} -> {v.__qualname__}: {data["resolver"].__qualname__}",
            )

        if origin == target:
            return _passthrough

        try:
            path = nx.shortest_path(self.graph, origin, target, weight="weight")
        except (nx.NetworkXNoPath, nx.NodeNotFound):
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
                logging.info(step.description)

                x = step.func(x)  # type: ignore

            if not isinstance(x, target):
                resolve_desc = "\n".join([step.description for step in steps])

                raise TypeError(
                    f"The resolved output with type '{type(x).__qualname__}' did not match target data type '{target.__qualname__}'; this is most likely a bug in a resolver function. Set log level to INFO debug resolver calls.\nResolvers used:\n{resolve_desc}"
                )

            return x

        return resolver_fn

    def resolve(self, value, astype: Type[Target]) -> Target:
        return self.find_resolve_func(type(value), astype)(value)

    def _plot_graph(self):
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

    # def find_resolvers(self, origin: Type[Origin], target: Type[Origin]):


def resolve(value: Any, *, astype: Type[Target]) -> Target:

    out_dtype = astype
    for in_dtype in value.__class__.__mro__:

        key = (in_dtype, out_dtype)
        try:
            resolver_fn = registry[key]
        except:
            continue

        resolved = resolver_fn(value)
        return resolved
    else:
        raise TypeError(
            f"Instance of {value.__class__} can not be resolved as {astype}"
        )


def resolver(f):

    # TODO: Input validation
    in_dtype = f.__annotations__["value"]
    out_dtype = f.__annotations__["return"]

    key = (in_dtype, out_dtype)
    if not key in registry:
        registry[key] = f

    return f


def resolve_params(f: Callable):

    signature = inspect.signature(f)

    def _resolve_arg(arg: Tuple[inspect.Parameter, Any]):
        param, value = arg
        if param.annotation is not None and get_origin(param.annotation) == Resolve:
            target = get_args(param.annotation)[0]
            value = resolve(value, astype=target)

        return param, value

    @wraps(f)
    def wrapper(*args, **kwargs):
        func_params = extract_func_params(args, kwargs, signature.parameters)

        args = list(func_params.items())[: len(args)]
        kwargs = list(func_params.items())[len(args) :]

        args = [_resolve_arg(a) for a in args]
        args = [v for _, v in args]

        kwargs = [_resolve_arg(a) for a in kwargs]
        kwargs = {k.name: v for k, v in kwargs}

        return f(*args, **kwargs)

    return wrapper
