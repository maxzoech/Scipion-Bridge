import os
from pathlib import Path
from functools import partial

from scipion_bridge.typed import proxy, resolve
from scipion_bridge.typed.proxy import Proxy, Out
from scipion_bridge.utils.environment.container import Container
from scipion_bridge.utils.environment import configure_default_env

import pytest
from pytest_mock import MockerFixture
from typing import Optional


class TempFileMock:

    def __init__(self):
        self.count = 0

    def new_temporary_file(self, suffix: str) -> os.PathLike:
        file = f"/tmp/temp_file_{self.count}{suffix}"
        self.count += 1

        return Path(file)

    def delete(self, path: os.PathLike):
        pass


def test_resolve_proxy():

    @proxy.proxify
    def foo(
        inputs: proxy.Proxy | Path, outputs: proxy.Proxy | Path
    ) -> Optional[proxy.Proxy]:
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


class Volume(Proxy):

    @classmethod
    def file_ext(cls):
        return ".vol"


def test_resolve_proxy_output():

    container = Container()
    container.wire(modules=[__name__, "scipion_bridge.typed.proxy"])

    temp_file_mock = TempFileMock()

    with container.temp_file_provider.override(temp_file_mock):
        p = resolve.resolve(Out(Volume), astype=Proxy)
        assert str(p.path) == "/tmp/temp_file_0.vol"

        del p


if __name__ == "__main__":
    test_resolve_proxy_output()
