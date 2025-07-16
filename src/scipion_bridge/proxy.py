import os

import inspect
import pathlib
import warnings

from functools import wraps
from typing import List

from collections import namedtuple

from .func_params import extract_func_params

from dependency_injector.wiring import Provide, inject
from .utils.environment.container import Container
from .utils.environment.temp_files import TemporaryFilesProvider


class Proxy:
    """
    :Description: A proxy that is backed by a temporary file.

    When you initialize this class, a temporary file is created to store
    intermediate results. You usually do not create instances of this class, and
    instead describe your proxy using the ``OutputInfo`` named tuple and have them
    created in the ``@proxify`` function.

    See :ref:`proxies` for more details.

    :param file_ext: The file extension of the wrapped file
    :param owned: If the file should be owned by the proxy. Owned files are
        deleted when the proxy object is dealloced


    """

    def __init__(self, file_ext: str, owned=False):
        self.file_ext = file_ext
        self.owned = owned

    @property
    def path(self):
        raise NotImplementedError("Implement in subclass")  # pragma: no cover

    def _ipython_display_(self):
        from .visualize import registry

        try:
            visualizer = registry.visualizers[self.file_ext]
        except KeyError:
            print(f"No visualizer registered for file extension {self.file_ext}")
            return

        visualizer.show(self.path)

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
            pass  # Fail silently

    def __str__(self):
        is_owned = "owned" if self.owned else "unowned"
        return f"<{self.__class__.__name__} for {self.path} ({is_owned})>"


class TempFileProxy(Proxy):
    """
    :Description:  proxy that is backed by a temporary file.

    When you initialize this class, a temporary file is created to store
    intermediate results. You usually do not create instances of this class,
    and instead describe your proxy using the ``OutputInfo`` named tuple and
    have them created in the ``@proxify`` function.

    See :ref:`proxies` for more details.

    :param file_ext: The file extension of the new file. ``None`` if the file should not have a type
    :type file_ext: str or None

    """

    def __init__(self, file_ext=None):
        """
        Create a proxy backed by a temporary file.

        In most cases you should pass an instance of `OutputInfo` to your
        function and let `@proxify` handle the instance creation.

        Args:
            - file_ext: The file extension of the underlying file, which is
            also interpreted as the _type_ of the proxy. If `None` the file will
            have no extension and the proxy is interpreted to be typed as any.
        """
        super().__init__(file_ext=file_ext, owned=True)

        self.suffix = "" if file_ext is None else f".{file_ext}"
        self.temp_file = None

    @inject
    def create_file(
        self,
        temp_file_provider: TemporaryFilesProvider = Provide[
            Container.temp_file_provider
        ],
    ) -> os.PathLike:
        return temp_file_provider.new_temporary_file(self.suffix)

    @property
    def path(self):
        if self.temp_file is None:
            self.temp_file = self.create_file()

        return self.temp_file

    @classmethod
    def proxy_for_string(cls, contents: str, *, file_ext):
        proxy = TempFileProxy(file_ext)
        with open(proxy.path, "w") as f:
            f.write(contents)

        return proxy

    @classmethod
    def concatenated_strings(cls, lines: List[str], *, file_ext):
        proxy = TempFileProxy(file_ext)
        with open(proxy.path, "w") as f:
            f.write("".join(lines))

        return proxy

    def reassign(self, new_ext: str):
        """
        Creates a reference proxy with specific type.

        This is useful if the underlying xmipp function adds its own file
        extension to the output path. In that case you can pass an untyped
        proxy that will pass a path like /tmp/xzy to xmipp; xmipp will write
        the result to a path like /tmp/xzy.vol. This function will create a
        ReferenceProxy for path '/tmp/xzy.vol'.

        The created ReferenceProxy is owned.

        Args:
            - new_ext: The file extension of the file created by scipion/xmipp
        """
        assert self.file_ext is None

        new_path = self.path + f".{new_ext}"

        if not os.path.exists(new_path):
            raise FileNotFoundError(
                f"No file found at '{new_path}'. Make sure the file extension matches. \
                                    If the external program writes files to a different known location, \
                                    initialize ReferenceProxy directly."
            )

        return ReferenceProxy(new_path, owned=True)


class ReferenceProxy(Proxy):
    """
    :Description: A proxy for an existing file.

    Use this proxy if you want to wrap an existing file in a proxy.

    .. note::
        You do not need to wrap input files in a ``ReferenceProxy``, you can
        pass the path directly to a function decorated with ``@proxify``.

    .. warning::
        If you set ``owned=True``, make sure that only one proxy object refers
        to the file. Otherwise, the underlying file will be deleted if one of
        our instances gets deallocated as ``Proxy`` objects are always assumed
        to have a one-to-one mapping with an underlying file.

    See :ref:`proxies` for more details.

    :param path: The path of the underlying file.
    :type path: str
    :param owned: If the file should be owned by the proxy. Owned files are deleted when the proxy object is deallocated.
    :type owned: bool

    """

    def __init__(self, path: os.PathLike, owned=False):
        file_ext = "".join(pathlib.Path(path).suffixes)[1:]

        super().__init__(file_ext, owned)
        self._path = path

    @property
    def path(self):
        return self._path


OutputInfo = namedtuple("OutputInfo", ["file_ext"])


def proxify(f, map_inputs=True, map_outputs=True):
    """
    :Description: Make a function compatible with proxies.

    XMIPP programs wrapped in the ``ffi`` module have a C-style interface
    that reads input files and writes its output to files. You can use them
    by passing file paths or creating temporary paths directly.

    If you do not want to manage temporary files directly, ``proxify`` provides
    syntactic sugar to provide a more ergonomic interface when working with them
    in Python:

    * If you pass a proxy object to any input argument, the path of its associated file is passed to the wrapped function.
    * For output parameters, pass an instance of the ``OutputInfo`` object. This function will create a proxy object, and passes the path of the temporary file to the underlying function, and return the proxy objects.

    .. note:: When using ``@proxify`` to return output values, the original return value of the function is lost.

    See :ref:`proxies` for more details.

    :param map_inputs: A boolean indicating if input proxies should be mapped
    :param map_outputs: A boolean indicating if output proxies should be mapped

    """

    signature = inspect.signature(f)

    @wraps(f)
    def wrapper(*args, **kwargs):
        # try:
        #     f.__wrapped__(*args, **kwargs)
        # except AttributeError as e:
        #     logging.warning(
        #         "Could not check function arguments at call site; this" \
        #         "may lead to undefined behavior and may be due " \
        #         "to an additional function wrapper: Please make sure to " \
        #         "decorate your wrapper with @functools.wraps(f)"
        #     )
        # TODO: Verify arguments in extract_func_params

        func_args = extract_func_params(args, kwargs, signature.parameters)
        func_args = {k.name: v for k, v in func_args.items()}

        # Replace input proxy objects with their path
        if map_inputs:
            func_args = {
                k: v.path if isinstance(v, Proxy) else v for k, v in func_args.items()
            }

        output_proxies = []
        if map_outputs:
            func_args = {
                k: TempFileProxy(v.file_ext) if isinstance(v, OutputInfo) else v
                for k, v in func_args.items()
            }

            for k, v in func_args.items():
                if isinstance(v, Proxy):
                    output_proxies.append(v)
                    func_args[k] = os.path.abspath(v.path)

        out_val = f(**func_args)

        outputs = out_val if isinstance(out_val, tuple) else (out_val,)
        outputs_are_proxies = all([isinstance(o, Proxy) for o in outputs])

        if outputs_are_proxies:
            # If the outputs are coming from another proxified function, just
            # return them as is
            return out_val

        if not (out_val == 0 or out_val == None) and map_outputs:
            warnings.warn(
                f"Wrapped function returns non-zero value; the value '{out_val}' will be discarded",
                UserWarning,
            )

        if len(output_proxies) == 0:
            return None
        elif len(output_proxies) == 1:
            return output_proxies[0]
        else:
            return tuple(output_proxies)

    return wrapper
