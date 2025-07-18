from functools import wraps
import inspect

from ..func_params import extract_func_params

from typing import (
    NewType,
    Type,
    Any,
    Optional,
    TypeVar,
    Generic,
    Callable,
    Union,
    get_origin,
    get_args,
    TYPE_CHECKING,
)

registry = {}

Target = TypeVar("Target")
Origin = TypeVar("Origin")


if TYPE_CHECKING:
    Resolve = Union[Target, Origin]
else:
    class Resolve(Generic[Target, Origin]):
        pass  # Marker Type


def resolver(f):

    # TODO: Input validation
    in_dtype = f.__annotations__["value"]
    out_dtype = f.__annotations__["return"]

    key = (in_dtype, out_dtype)
    if not key in registry:
        registry[key] = f

    return f


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


def resolve_params(f: Callable):

    signature = inspect.signature(f)

    def _resolve_arg(arg: tuple[inspect.Parameter, Any]):
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

        print(args, kwargs)

        return f(*args, **kwargs)

    return wrapper
