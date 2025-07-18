import scipion_bridge.typed.resolve as resolve
from scipion_bridge.typed.proxy import Proxy, Out
from typing import Any


def test_resolved_func():

    @resolve.resolve_params
    def foo(bar: resolve.Resolve[str, int], number: float, value):
        assert bar == "10"
        assert number == 42.0
        assert value == "Test"

    foo(10, number=42.0, value="Test")


if __name__ == "__main__":
    test_resolved_func()
