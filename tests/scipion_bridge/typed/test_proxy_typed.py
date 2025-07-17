import os
from pathlib import Path
from functools import partial

from scipion_bridge.typed import proxy, resolve
from scipion_bridge.utils.environment.container import Container

import pytest
from pytest_mock import MockerFixture


class TempFileMock:

    def __init__(self):
        self.count = 0

    def new_temporary_file(self, suffix: str) -> os.PathLike:
        file = f"/tmp/temp_file_{self.count}{suffix}"
        self.count += 1

        return file

    def delete(path: os.PathLike):
        pass


def test_resolve_proxy():

    @proxy.proxify
    def foo(input_proxy: proxy.Proxy | Path):
        print(input_proxy)

    input_proxy = proxy.Proxy(Path("/path/to/file.txt"), role=proxy.Proxy.Role.OUTPUT)
    out = foo(input_proxy)

    print(out)

    foo(Path("/this/is/a/test"))

    print(foo.__annotations__["input_proxy"])


if __name__ == "__main__":
    test_resolve_proxy()
