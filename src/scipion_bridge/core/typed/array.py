import numpy as np
from .resolve import current_registry

from functools import partial, wraps
from typing import Type


class ArrayConvertable:

    def __init__(self) -> None:

        resolver_fn = wraps(resolve_output_to_proxy)(
            partial(resolve_output_to_proxy, cls=type(self))
        )

        current_registry().add_resolver(np.ndarray, type(self), resolver_fn)

    def to_numpy(self):
        raise NotImplementedError

    @classmethod
    def from_numpy(cls, data: np.ndarray):
        raise NotImplementedError

    def __array__(self):
        return self.to_numpy()


def resolve_output_to_proxy(
    value: np.ndarray, cls: Type[ArrayConvertable]
) -> ArrayConvertable:
    return cls.from_numpy(value)
