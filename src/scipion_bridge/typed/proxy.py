import os
import inspect
from pathlib import Path
import logging
import warnings
from enum import Enum
from functools import partial, wraps
import shutil

from dependency_injector.wiring import Provide, inject
from ..utils.environment.container import Container
from ..utils.environment.temp_files import TemporaryFilesProvider
from ..utils.arc import manager as arc_manager
from ..func_params import extract_func_params

from .resolve import registry, resolve_params, resolver
from typing import Optional, TypeVar, Generic, Type, Union
from typing_extensions import TypeAlias

Casted = TypeVar("Casted")
T = TypeVar("T")


class FuncParam:
    def __init__(
        self, str_rep: str, dtype: Optional[Type[T]] = None, managed_proxy=False
    ) -> None:
        self.str_rep = str_rep
        self.dtype = dtype
        self.managed_proxy = managed_proxy

    def __repr__(self) -> str:
        return f"{FuncParam.__name__} ({self.str_rep}, dtype={self.dtype}, managed_proxy={self.managed_proxy})"


class Proxy:

    def __init__(self, path: os.PathLike, managed=False):
        self.path = Path(path)
        self.managed = managed

        if self.managed == True:
            arc_manager.add_reference(self.path)

    @classmethod
    def file_ext(cls) -> Optional[str]:
        return None

    def typed(self, *, astype: Type[Casted], copy_data=True) -> Casted:
        if self.file_ext() is not None:
            raise TypeError(
                f"Cannot add type to proxy with existing type {self.file_ext()}"
            )

        assert issubclass(astype, Proxy)

        new_ext = astype.file_ext()
        assert isinstance(new_ext, str)

        new_path = self.path.with_name(f"{self.path.name}{new_ext}")
        if copy_data:
            shutil.copy(str(self.path), str(new_path))

        new_proxy = astype(
            new_path,
            managed=self.managed,
        )

        return new_proxy

    @inject
    def __del__(
        self,
        temp_file_provider: TemporaryFilesProvider = Provide[
            Container.temp_file_provider
        ],
    ):

        try:
            if self.managed == True:
                if arc_manager.get_count(self.path) == 1:
                    temp_file_provider.delete(self.path)

        except Exception as e:
            logging.warning(f"Failed to delete file at {self.path}: {e}")
            pass  # Fail silently

        if self.managed:
            arc_manager.remove_reference(self.path)

    def __str__(self):
        is_owned = "managed" if self.managed else "unmanaged"
        return f"<{self.__class__.__name__} for {self.path} ({is_owned})>"


class Output:
    def __init__(self, dtype: Type[T]) -> None:
        assert issubclass(dtype, Proxy)
        self.dtype = dtype


ProxyParam: TypeAlias = Union[Proxy, Path, Output]


def proxify(f):

    signature = inspect.signature(f)

    def _proxy_from_func_param(param: FuncParam):
        cls = (
            param.dtype if param.dtype is not None else Proxy
        )  # Create new untyped proxy if we only pass a path here
        assert issubclass(cls, Proxy)

        return cls(Path(param.str_rep), managed=param.managed_proxy)

    @wraps(f)
    def wrapped(*args, **kwargs):

        func_args = extract_func_params(args, kwargs, signature)

        should_return = {
            k: isinstance(v.default, Output) for k, v in signature.parameters.items()
        }

        resolved = [
            (param.name, registry.resolve(v, astype=FuncParam))
            for param, v in func_args.items()
        ]

        resolved_args = [v.str_rep for _, v in resolved[: len(args)]]
        resolved_kwargs = {k: v.str_rep for k, v in resolved[len(args) :]}

        out_val = f(*resolved_args, **resolved_kwargs)

        return_vals = [
            _proxy_from_func_param(v) for k, v in resolved if should_return[k]
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


# def proxify(f):

#     # @resolve_params
#     @mange_return_values
#     @wraps(f)
#     def wrapper(*args, **kwargs):
#         return f(*args, **kwargs)

#     return wrapper


@resolver
def resolve_path_to_func_param(value: Path) -> FuncParam:
    return FuncParam(str(value))


@resolver
def resolve_str_to_func_param(value: str) -> FuncParam:
    return FuncParam(value)


@resolver
def resolve_proxy_to_func_param(value: Proxy) -> FuncParam:
    return FuncParam(str(value.path), type(value), managed_proxy=value.managed)


@resolver
@inject
def resolve_output_to_proxy(
    value: Output,
    temp_file_provider: TemporaryFilesProvider = Provide[Container.temp_file_provider],
) -> Proxy:

    file_ext = value.dtype.file_ext()
    file_ext = file_ext if file_ext is not None else ""

    temp_file = temp_file_provider.new_temporary_file(file_ext)

    new_proxy = value.dtype(Path(temp_file), managed=True)

    assert isinstance(new_proxy, Proxy)
    return new_proxy
