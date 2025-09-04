from functools import wraps, partial
import inspect
import networkx as nx
import logging
import warnings
import time
from collections import namedtuple
from functools import reduce

from ..func_params import extract_func_params
from .dijkstra import find_shortest_path, PathfindingContainer

from typing import (
    Tuple,
    Set,
    List,
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


def _downcast(x):
    return x


def _passthrough(x):
    return x


def _find_calling_frame():
    frame = inspect.currentframe()
    while frame is not None:
        if not frame.f_globals["__name__"].startswith(__package__):
            return frame
        else:
            frame = frame.f_back
    else:
        raise RuntimeError("Could not find calling frame. This is a bug.")


class ScopedPathfindingContainer(PathfindingContainer):

    ResolverNode = namedtuple("ResolverNode", ["resolver_fn", "module"])

    def __init__(
        self,
        value: Optional[Any],
        previous: Optional[Any],
        weight: int,
        incoming_edge_attributes: Optional[ResolverNode],
        local_scope_name: str,
    ) -> None:
        super().__init__(value, previous, weight)

        self.edge_attributes = incoming_edge_attributes
        self.local_scope_name = local_scope_name

    @property
    def is_local_scope(self):
        assert self.edge_attributes is not None

        return self.edge_attributes.module.startswith(self.local_scope_name)

    @property
    def resolution_priority(self):
        if self.is_local_scope:
            return 0  # Higher priority
        else:
            return 1

    def __lt__(self, other):
        assert isinstance(other, ScopedPathfindingContainer)

        assert self.edge_attributes is not None
        assert other.edge_attributes is not None

        if not self.weight == other.weight:
            return self.weight < other.weight
        else:
            if not self.resolution_priority == other.resolution_priority:
                return self.resolution_priority < other.resolution_priority
            else:

                symbol_path = f"{self.edge_attributes.module}.{self.edge_attributes.resolver_fn.__qualname__}"
                other_symbol_path = f"{other.edge_attributes.module}.{other.edge_attributes.resolver_fn.__qualname__}"

                path_length = len(symbol_path.split("."))
                other_path_length = len(other_symbol_path.split("."))

                if (
                    other_path_length == path_length
                    and self.edge_attributes.resolver_fn
                    is not other.edge_attributes.resolver_fn
                ):

                    warnings.warn(
                        f"Found ambiguous resolvers {symbol_path} and {other_symbol_path} during type resolution.",
                    )

                return other_path_length < path_length


def build_default_container(
    graph: nx.DiGraph,
    value: Type,
    previous: Optional[Type],
    weight: int,
    local_scope_name: str,
):
    if not previous:
        edge_attributes = None
    else:
        attrs = graph.get_edge_data(previous, value)
        edge_attributes = ScopedPathfindingContainer.ResolverNode(
            attrs["resolver"], attrs["module"]
        )
    return ScopedPathfindingContainer(
        value,
        previous,
        weight,
        edge_attributes,
        local_scope_name,
    )


class Registry:

    def __init__(self) -> None:
        self.graph = nx.DiGraph()

    def get_registered_modules(self) -> Set[str]:
        modules = {v[2] for v in self.graph.edges.data("module")}  # type: ignore
        return modules

    @staticmethod
    def _namespace_from_symbol(*, module: str, qualname: str, strip_last=False):
        path = f"{module}.{qualname}"
        if strip_last:
            path = path.split(".")[:-1]
            if path[-1] == "<locals>":
                path = path[:-1]
            path = ".".join(path)

        return path  #

    def add_resolver(
        self,
        origin: Type[Origin],
        target: Type[Origin],
        resolver: Callable,
        namespace: Optional[str] = None,
    ):

        if namespace is None:
            frame = _find_calling_frame()
            module = frame.f_globals["__name__"]
            name = frame.f_code.co_qualname
            namespace = Registry._namespace_from_symbol(
                module=module, qualname=name, strip_last=True
            )

        if self.graph.has_edge(origin, target):
            edge = self.graph.edges[(origin, target)]

            if edge["module"] == namespace and not resolver is edge["resolver"]:
                warnings.warn(
                    f"Attempted register a resolver for existing transform '{origin.__qualname__}' -> '{target.__qualname__}' ('{edge['resolver'].__qualname__}' vs '{resolver.__qualname__}')",
                    UserWarning,
                )
                return

        def _add_downcasts(subclass: Type):
            for weight, dtype in enumerate(subclass.__mro__):
                if origin == dtype:
                    continue

                self.graph.add_edge(
                    subclass,
                    dtype,
                    resolver=_downcast,
                    weight=weight,
                    module=__package__,
                )

        self.graph.add_edge(
            origin, target, resolver=resolver, weight=0, module=namespace
        )

        # Add edges to downcast data
        _add_downcasts(origin)
        _add_downcasts(target)

    def find_resolve_func(
        self,
        namespace: Set[str],
        origin: Type[Origin],
        target: Type[Target],
        intermediate: Optional[Type[Intermediate]] = None,
        local_scope_name: Optional[str] = None,
    ):
        assert local_scope_name is not None

        def _make_step(edge, data):
            u, v = edge
            fn = data["resolver"]
            mod = data["module"]

            return ResolveStep(
                fn,
                f"{u.__qualname__} -> {v.__qualname__}: {fn.__qualname__} ({mod})",
            )

        if origin == target:
            return _passthrough

        selected_edges = [
            (u, v, e)
            for u, v, e in self.graph.edges(data=True)
            if e["module"] in namespace
        ]
        subgraph = nx.DiGraph(selected_edges)

        # Find the first subclass that is in the graph
        for dtype in origin.__mro__:
            if dtype in subgraph:
                upcast_origin = dtype
                break
        else:
            raise TypeError(
                f"'{origin.__qualname__}' could not be resolved as '{target.__qualname__}'"
            )

        try:
            path = find_shortest_path(
                subgraph,
                upcast_origin,
                target,
                intermediate,
                weight="weight",
                container_builder=partial(
                    build_default_container, local_scope_name=local_scope_name
                ),
            )
        except (nx.NetworkXNoPath, nx.NodeNotFound, StopIteration):
            raise TypeError(
                f"'{origin.__qualname__}' could not be resolved as '{target.__qualname__}'"
            )

        steps = [
            _make_step((u, v), subgraph.get_edge_data(u, v))
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

        def _find_module(value: Any) -> Optional[str]:
            try:
                if inspect.ismodule(value):
                    return value.__name__
                else:
                    return value.__module__
            except AttributeError:
                return None

        def _expand_namespace(namespace: str, expanded: List[str]) -> Set[str]:
            if not namespace:
                return set(expanded)
            else:
                path = namespace.split(".")
                head, tail = path[0], path[1:]

                next_el = f"{expanded[-1]}.{head}" if expanded else head

                return _expand_namespace(".".join(tail), expanded + [next_el])

        start = time.time()

        # Find imported modules to construct namespace
        frame = _find_calling_frame()
        calling_module: str = frame.f_globals["__name__"]
        calling_func: str = frame.f_code.co_qualname
        calling_namespace = Registry._namespace_from_symbol(
            module=calling_module, qualname=calling_func
        )

        visible_modules = {
            v for v in map(_find_module, frame.f_globals.values()) if v is not None
        }
        visible_modules.add(calling_namespace)

        # Expand namespaces: "foo.bar.func" -> {foo, foo.bar, foo.bar.func}
        visible_modules = {m for n in visible_modules for m in _expand_namespace(n, [])}

        # Get the namespaces registered in the graph and expand
        registered_modules = self.get_registered_modules()
        registered_modules = {
            m for n in registered_modules for m in _expand_namespace(n, [])
        }

        # The union of the visible modules and registered modules is the available namespace
        namespaces = visible_modules & registered_modules

        intermediate_desc = (
            f" (via '{intermediate.__qualname__}')" if intermediate is not None else ""
        )

        namespaces_desc = [f"'{n}'" for n in namespaces]
        namespaces_desc = ", ".join(namespaces_desc).rstrip()

        logging.info(
            f"Resolve '{type(value).__qualname__}' -> '{astype.__qualname__}'{intermediate_desc} with namespaces {namespaces_desc} (caller in '{calling_namespace}')"
        )

        resolve_fn = self.find_resolve_func(
            namespaces, type(value), astype, intermediate, calling_namespace
        )
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

    def _plot_graph(self, G=None):  # pragma: no cover
        import networkx as nx
        import matplotlib.pyplot as plt

        if G is None:
            G = self.graph

        pos = nx.spring_layout(G, seed=7)
        nx.draw_networkx_nodes(G, pos, node_size=250)
        nx.draw_networkx_edges(G, pos, width=1)

        nx.draw_networkx_labels(G, pos, font_size=12, font_family="sans-serif")

        edge_weights = nx.get_edge_attributes(G, "weight")
        edge_modules = nx.get_edge_attributes(G, "module")

        edge_labels = {}
        for k in edge_weights.keys():
            edge_labels[k] = f"{edge_modules[k]} ({edge_weights[k]})"

        nx.draw_networkx_edge_labels(G, pos, edge_weights)

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

    namespace = Registry._namespace_from_symbol(
        module=f.__module__,
        qualname=f.__qualname__,
        strip_last=True,
    )

    registry.add_resolver(in_dtype, out_dtype, f, namespace)

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
