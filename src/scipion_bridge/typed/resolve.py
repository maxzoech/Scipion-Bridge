from typing import Callable, TypeVar, NewType, Type, Any, Tuple, Generic

T = TypeVar("T")

registry = {}


def resolver(f):

    # TODO: Input validation
    in_dtype = f.__annotations__["value"]
    out_dtype = f.__annotations__["return"]

    key = (in_dtype, out_dtype)
    if not key in registry:
        registry[key] = f

    return f


def resolve(value: Any, *, astype: Type) -> T:

    for in_dtype in value.__class__.__mro__:
        out_dtype = astype

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


class Proxy:
    pass


class Volume(Proxy):
    pass


@resolver
def resolve_volume_to_str(value: Volume) -> str:
    return "Volume data"


vol = Volume()
print(registry)
print(resolve(vol, astype=str))
# print(resolve(vol, astype=Proxy))
