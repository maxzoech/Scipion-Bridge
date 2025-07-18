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

from . import resolve
from typing import Optional, TypeVar, Generic, Type, Union
from typing_extensions import TypeAlias

FileLocation: TypeAlias = str

Casted = TypeVar("Casted")


class Proxy:
    class Role(Enum):
        INPUT = 0
        OUTPUT = 1

    def __init__(self, path: os.PathLike, role: Role, owned=False):
        self.path = Path(path)
        self.role = role

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
            role=self.role,
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


ProxyParam: TypeAlias = Union[Proxy, Path]


def mange_return_values(f):

    signature = inspect.signature(f)

    @wraps(f)
    def wrapped(*args, **kwargs):

        func_args = extract_func_params(args, kwargs, signature.parameters)

        resolved_args = [str(resolve.resolve(a, astype=FileLocation)) for a in args]
        resolved_kwargs = {
            k: str(resolve.resolve(v, astype=FileLocation)) for k, v in kwargs.items()
        }

        out_val = f(*resolved_args, **resolved_kwargs)

        return_vals = [
            v
            for v in func_args.values()
            if isinstance(v, Proxy)
            if v.role == Proxy.Role.OUTPUT
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

        for v in return_vals:
            v.role = (
                Proxy.Role.INPUT
            )  # Input the proxy role here because it will be the input to the next function

        if len(return_vals) == 0:
            return out_val
        elif len(return_vals) == 1:
            return return_vals[0]
        else:
            return tuple(return_vals)

    return wrapped


def proxify(f):

    @resolve.resolve_params
    @mange_return_values
    @wraps(f)
    def wrapper(*args, **kwargs):
        return f(*args, **kwargs)

    return wrapper


T = TypeVar("T")


class Output:
    def __init__(self, dtype: Type[T]) -> None:
        assert issubclass(dtype, Proxy)
        self.dtype = dtype


@resolve.resolver
def resolve_path_to_file_location(value: Path) -> FileLocation:
    return FileLocation(value)


@resolve.resolver
def resolve_proxy_to_file_location(value: Proxy) -> FileLocation:
    return resolve.resolve(value.path, astype=FileLocation)


@resolve.resolver
@inject
def resolve_output_to_proxy(
    value: Output,
    temp_file_provider: TemporaryFilesProvider = Provide[Container.temp_file_provider],
) -> Proxy:

    file_ext = value.dtype.file_ext()
    file_ext = file_ext if file_ext is not None else ""

    temp_file = temp_file_provider.new_temporary_file(file_ext)

    new_proxy = value.dtype(Path(temp_file), owned=True, role=Proxy.Role.OUTPUT)

    assert isinstance(new_proxy, Proxy)
    return new_proxy
