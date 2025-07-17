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
from typing import Optional, NewType, TypeAlias


# class FileLocation:
#     def __init__(self, value: str) -> None:
#         self.value = value

#     def __str__(self) -> str:
#         return self.value

FileLocation: TypeAlias = str


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


def proxify(f):

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

        if not (out_val == 0 or out_val == None):
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


@resolve.resolver
def resolve_path_to_file_location(value: Path) -> FileLocation:
    return FileLocation(value)


@resolve.resolver
def resolve_proxy_to_file_location(value: Proxy) -> FileLocation:
    return resolve.resolve(value.path, astype=FileLocation)
