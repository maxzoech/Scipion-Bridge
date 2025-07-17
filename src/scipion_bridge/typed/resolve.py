import functools
from typing import NewType, Type, Any, Optional, TypeVar

registry = {}

T = TypeVar("T")


def resolver(f):

    # TODO: Input validation
    in_dtype = f.__annotations__["value"]
    out_dtype = f.__annotations__["return"]

    key = (in_dtype, out_dtype)
    if not key in registry:
        registry[key] = f

    return f


def resolve(value: Any, *, astype: Type[T]) -> T:

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
