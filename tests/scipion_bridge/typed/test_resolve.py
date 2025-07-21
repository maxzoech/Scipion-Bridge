import scipion_bridge.typed.resolve as resolve
from scipion_bridge.typed.proxy import Proxy, Output
from typing import Any
import logging

import pytest


def test_basic_resolve():

    logging.getLogger().setLevel(logging.INFO)

    registry = resolve.Registry()
    registry.add_resolver(object, str, lambda x: str(x))
    registry.add_resolver(float, int, lambda x: int(x))

    func = registry.find_resolve_func(float, str)
    resolved = func(2.5)

    assert resolved == "2.5"


def test_resolve_faulty_resolver():
    registry = resolve.Registry()
    registry.add_resolver(object, str, lambda x: int(x))  # Returns wrong type here
    registry.add_resolver(float, int, lambda x: int(x))

    with pytest.raises(TypeError):
        func = registry.find_resolve_func(float, str)
        _ = func(2.5)


def test_unresolvable_types_error():
    registry = resolve.Registry()
    registry.add_resolver(float, int, lambda x: int(x))  # Returns wrong type here
    registry.add_resolver(bool, int, lambda x: int(x))

    with pytest.raises(TypeError):
        func = registry.find_resolve_func(float, bool)
        _ = func(2.5)

    with pytest.raises(TypeError):
        func = registry.find_resolve_func(float, str)
        _ = func(2.5)


def test_resolve_proxy():
    import os
    from pathlib import Path

    class TextFile(Proxy):

        @classmethod
        def file_ext(cls):
            return ".txt"

    def _resolve_output_to_proxy(output: Output):
        ext = str(output.dtype.file_ext())
        return output.dtype(Path("/path/to/output" + ext), owned=False)

    registry = resolve.Registry()
    registry.add_resolver(Path, str, lambda x: str(x))
    registry.add_resolver(Proxy, Path, lambda x: x.path)
    registry.add_resolver(Output, Proxy, _resolve_output_to_proxy)

    resolved_path = registry.resolve(Proxy(Path("/path/to/file.txt")), str)
    assert resolved_path == "/path/to/file.txt"

    resolved_path = registry.resolve(Proxy("/path/to/file.txt"), str)  # type: ignore
    assert resolved_path == "/path/to/file.txt"

    resolved_proxy = registry.resolve(Output(TextFile), Proxy)
    assert str(resolved_proxy.path) == "/path/to/output.txt"

    resolved_path = registry.resolve(Output(TextFile), str)
    assert resolved_path == "/path/to/output.txt"


def test_resolved_func():

    @resolve.resolve_params
    def foo(bar: resolve.Resolve[str, int], number: float, value):
        assert bar == "10"
        assert number == 42.0
        assert value == "Test"

    foo(10, number=42.0, value="Test")


@pytest.mark.skip(reason="Resolving classes with their identity not yet implemented")
def test_resolve_passthrough():
    @resolve.resolve_params
    def foo(bar: resolve.Resolve[int, float]):
        assert bar == 42

    foo(42)


if __name__ == "__main__":
    test_resolve_proxy()
