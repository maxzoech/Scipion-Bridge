import os
import inspect
from pathlib import Path
import logging
import warnings
from enum import Enum
from functools import partial, wraps

from dependency_injector.wiring import Provide, inject
from ..utils.environment.container import Container
from ..utils.environment.temp_files import TemporaryFilesProvider
from ..func_params import extract_func_params

from .resolve import registry, resolve_params, resolver
from typing import Optional, TypeVar, Generic, Type, Union
from typing_extensions import TypeAlias

FileLocation: TypeAlias = str

Casted = TypeVar("Casted")
T = TypeVar("T")


class Proxy:

    def __init__(self, path: os.PathLike, owned=False):
        self.path = Path(path)
        self.owned = owned

    @classmethod
    def file_ext(cls) -> Optional[str]:
        return None

    def typed(self, *, astype: Type[Casted], append_ext=True) -> Casted:
        if self.file_ext() is not None:
            raise TypeError(
                f"Cannot add type to proxy with existing type {self.file_ext()}"
            )

        assert issubclass(astype, Proxy)

        new_ext = astype.file_ext()
        assert isinstance(new_ext, str)

        new_path = (
            self.path.with_name(f"{self.path.name}{new_ext}")
            if append_ext
            else self.path
        )

        new_proxy = astype(
            new_path,
            owned=self.owned,
        )
        self.owned = False  # Transfer ownership here; # TODO: More robust system to manage ownership

        return new_proxy

    @inject
    def __del__(
        self,
        temp_file_provider: TemporaryFilesProvider = Provide[
            Container.temp_file_provider
        ],
    ):

        try:
            if self.owned == True:
                temp_file_provider.delete(self.path)
        except:
            logging.warning(f"Failed to delete file at {self.path} for proxy")
            pass  # Fail silently

    def __str__(self):
        is_owned = "owned" if self.owned else "unowned"
        return f"<{self.__class__.__name__} for {self.path} ({is_owned})>"


class Output:
    def __init__(self, dtype: Type[T]) -> None:
        assert issubclass(dtype, Proxy)
        self.dtype = dtype


ProxyParam: TypeAlias = Union[Proxy, Path, Output]


def mange_return_values(f):

    signature = inspect.signature(f)

    def _wrap_as_untyped_proxy(value):
        if isinstance(value, Proxy):
            return value
        else:
            assert isinstance(value, os.PathLike)
            return Proxy(Path(value), owned=False)

    @wraps(f)
    def wrapped(*args, **kwargs):

        func_args = extract_func_params(args, kwargs, signature.parameters)
        should_return = {
            k: isinstance(v.default, Output) for k, v in signature.parameters.items()
        }

        resolved_args = [str(registry.resolve(a, astype=FileLocation)) for a in args]
        resolved_kwargs = {
            k: str(registry.resolve(v, astype=FileLocation)) for k, v in kwargs.items()
        }

        out_val = f(*resolved_args, **resolved_kwargs)

        # TODO: Move wrapping into untyped proxy to type resolution system
        return_vals = [
            _wrap_as_untyped_proxy(v)
            for k, v in func_args.items()
            if should_return[k.name]
            # if isinstance(v, Proxy)
        ]

        try:
            outputs = out_val if isinstance(out_val, tuple) else tuple([out_val])
            outputs_are_proxies = all(isinstance(o, Proxy) for o in outputs)
        except TypeError as e:
            outputs_are_proxies = False

        if not (out_val == 0 or out_val == None or outputs_are_proxies):
            warnings.warn(
                f"Wrapped function returns non-zero value; the value '{out_val}' will be discarded",
                UserWarning,
            )

        if len(return_vals) == 0:
            return out_val
        elif len(return_vals) == 1:
            return return_vals[0]
        else:
            return tuple(return_vals)

    return wrapped


def proxify(f):

    @resolve_params
    @mange_return_values
    @wraps(f)
    def wrapper(*args, **kwargs):
        return f(*args, **kwargs)

    return wrapper


@resolver
def resolve_path_to_file_location(value: Path) -> FileLocation:
    return FileLocation(value)


@resolver
def resolve_proxy_to_file_location(value: Proxy) -> FileLocation:
    return registry.resolve(value.path, astype=FileLocation)


@resolver
@inject
def resolve_output_to_proxy(
    value: Output,
    temp_file_provider: TemporaryFilesProvider = Provide[Container.temp_file_provider],
) -> Proxy:

    file_ext = value.dtype.file_ext()
    file_ext = file_ext if file_ext is not None else ""

    temp_file = temp_file_provider.new_temporary_file(file_ext)

    new_proxy = value.dtype(Path(temp_file), owned=True)

    assert isinstance(new_proxy, Proxy)
    return new_proxy
