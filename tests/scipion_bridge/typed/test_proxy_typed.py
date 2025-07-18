import os
from pathlib import Path
from functools import partial

from scipion_bridge.typed import proxy, resolve
from scipion_bridge.typed.proxy import proxify
from scipion_bridge.typed.proxy import Proxy, ProxyParam, Output
from scipion_bridge.utils.environment.container import Container
from scipion_bridge.utils.environment import configure_default_env

import pytest
from pytest_mock import MockerFixture
from typing import Optional, Union, Tuple


class TempFileMock:

    def __init__(self):
        self.count = 0

    def new_temporary_file(self, suffix: str) -> os.PathLike:
        file = f"/tmp/temp_file_{self.count}{suffix}"
        self.count += 1

        return Path(file)

    def delete(self, path: os.PathLike):
        pass


class Volume(Proxy):

    @classmethod
    def file_ext(cls):
        return ".vol"


def test_resolve_proxy_output():

    container = Container()
    container.wire(modules=[__name__, "scipion_bridge.typed.proxy"])

    temp_file_mock = TempFileMock()

    with container.temp_file_provider.override(temp_file_mock):
        p = resolve.resolve(Output(Volume), astype=Proxy)
        assert str(p.path) == "/tmp/temp_file_0.vol"

        del p


def test_resolve_proxy():

    @proxify
    def foo(inputs: ProxyParam, outputs: ProxyParam) -> Optional[proxy.Proxy]:
        assert inputs == "/path/to/input.txt"
        assert outputs == "/path/to/output.txt"

    input_proxy = proxy.Proxy(Path("/path/to/input.txt"), role=proxy.Proxy.Role.INPUT)
    output_proxy = proxy.Proxy(
        Path("/path/to/output.txt"), role=proxy.Proxy.Role.OUTPUT
    )

    out = foo(input_proxy, output_proxy)
    assert out is not None
    assert str(out.path) == "/path/to/output.txt"

    out = foo(Path("/path/to/input.txt"), Path("/path/to/output.txt"))
    assert out is None


def test_resolve_proxy_multi_output():

    @proxify
    def foo(
        output_1: resolve.Resolve[Proxy, Output] = Output(Volume),
        output_2: resolve.Resolve[Proxy, Output] = Output(Volume),
    ):
        pass

    container = Container()
    container.wire(modules=[__name__, "scipion_bridge.typed.proxy"])

    temp_file_mock = TempFileMock()
    with container.temp_file_provider.override(temp_file_mock):
        output: Tuple[Proxy, Proxy] = foo()  # type: ignore

        assert str(output[0].path) == "/tmp/temp_file_0.vol"
        assert str(output[1].path) == "/tmp/temp_file_1.vol"


class TextFile(Proxy):

    @classmethod
    def file_ext(cls) -> Optional[str]:
        return ".txt"


@pytest.mark.skip(reason="Implicitly resolving types not implemented yet")
def test_nested_proxies():

    @proxify
    def func_1(output_path: resolve.Resolve[Proxy, Output]):
        # assert isinstance(output_path, str)
        assert isinstance(output_path, str)

        with open(output_path, "w+") as f:

            f.write("Write from func 1")

    @proxify
    def func_2(output_path: resolve.Resolve[Proxy, Output]):
        return func_1(output_path)

    container = Container()
    container.wire(modules=[__name__, "scipion_bridge.typed.proxy"])

    temp_file_mock = TempFileMock()
    with container.temp_file_provider.override(temp_file_mock):
        output = func_2(Output(TextFile))
        assert isinstance(output, Proxy)
        assert str(output.path) == "/tmp/temp_file_0.txt"

        with open(output.path) as f:
            assert f.read() == "Write from func 1"


def test_proxify_with_params():

    @proxify
    def foo(
        inputs: ProxyParam,
        outputs: resolve.Resolve[Proxy, Output] = Output(Volume),
        bar: Optional[Tuple] = None,
        value=None,
    ):

        assert inputs == "/path/to/inputs.txt"
        assert outputs == "/tmp/temp_file_0.vol"
        assert bar == "1 2 3"
        assert value == "42"

    container = Container()
    container.wire(modules=[__name__, "scipion_bridge.typed.proxy"])

    temp_file_mock = TempFileMock()

    with container.temp_file_provider.override(temp_file_mock):
        out = foo(Path("/path/to/inputs.txt"), bar=(1, 2, 3), value=42)

        assert out is not None
        assert str(out.path) == "/tmp/temp_file_0.vol"

        del out


if __name__ == "__main__":
    test_nested_proxies()
