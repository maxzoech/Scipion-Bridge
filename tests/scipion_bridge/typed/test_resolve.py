import scipion_bridge.typed.resolve as resolve
from scipion_bridge.typed.proxy import Proxy, Output
from typing import Any

import pytest


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
    test_resolved_func()
