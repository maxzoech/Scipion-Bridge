import os
import warnings
from pathlib import Path
from functools import partial

from scipion_bridge.typed import proxy
from scipion_bridge.typed.resolve import registry, Resolve, Registry
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
        p = registry.resolve(Output(Volume), astype=Proxy)
        assert str(p.path) == "/tmp/temp_file_0.vol"

        del p


class TextFile(Proxy):

    @classmethod
    def file_ext(cls) -> Optional[str]:
        return ".txt"


def test_resolve_proxy():
    import os
    from pathlib import Path

    def _resolve_output_to_proxy(output: Output):
        ext = str(output.dtype.file_ext())
        return output.dtype(Path("/path/to/output" + ext), owned=False)

    registry = Registry()
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


@pytest.mark.skip("Fix finding subclass first")
def test_resolve_proxified():

    @proxify
    def foo(
        inputs: ProxyParam, outputs: ProxyParam = Output(TextFile)
    ) -> Optional[proxy.Proxy]:
        assert inputs == "/path/to/input.txt"
        assert outputs == "/path/to/output.txt"

    input_proxy = proxy.Proxy(Path("/path/to/input.txt"))
    output_proxy = proxy.Proxy(Path("/path/to/output.txt"))

    out = foo(input_proxy, output_proxy)
    assert out is not None
    assert str(out.path) == "/path/to/output.txt"

    out = foo(Path("/path/to/input.txt"), Path("/path/to/output.txt"))
    assert isinstance(out, Proxy)
    assert out.path == Path("/path/to/output.txt")
    assert out.owned == False


@pytest.mark.skip("Fix finding subclass first")
def test_resolve_proxy_multi_output():

    @proxify
    def foo(
        output_1: Resolve[Proxy, Output] = Output(Volume),
        output_2: Resolve[Proxy, Output] = Output(Volume),
    ):
        pass

    container = Container()
    container.wire(modules=[__name__, "scipion_bridge.typed.proxy"])

    temp_file_mock = TempFileMock()
    with container.temp_file_provider.override(temp_file_mock):
        output: Tuple[Proxy, Proxy] = foo()  # type: ignore

        assert str(output[0].path) == "/tmp/temp_file_0.vol"
        assert str(output[1].path) == "/tmp/temp_file_1.vol"


@pytest.mark.skip(reason="Implicitly resolving types not implemented yet")
def test_nested_proxies():

    @proxify
    def func_1(output_path: Resolve[Proxy, Output]):
        # assert isinstance(output_path, str)
        assert isinstance(output_path, str)

        with open(output_path, "w+") as f:

            f.write("Write from func 1")

    @proxify
    def func_2(output_path: Resolve[Proxy, Output]):
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


@pytest.mark.skip("Fix finding subclass first")
def test_return_value_warning():

    @proxify
    def foo(output: Resolve[str, Output]):
        del output
        return 42

    @proxify
    def func_1(output_path: Resolve[Proxy, Output]):
        pass

    @proxify
    def func_2():
        return func_1(Output(TextFile))

    container = Container()
    container.wire(modules=[__name__, "scipion_bridge.typed.proxy"])

    temp_file_mock = TempFileMock()
    with container.temp_file_provider.override(temp_file_mock):
        with pytest.warns(UserWarning):
            foo(Output(TextFile))

        with warnings.catch_warnings(record=True) as w:
            func_2()

            assert len(w) == 0


@pytest.mark.skip("Fix finding subclass first")
def test_proxify_with_params():

    @proxify
    def foo(
        inputs: ProxyParam,
        outputs: Resolve[Proxy, Output] = Output(Volume),
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

    registry._plot_graph()

    with container.temp_file_provider.override(temp_file_mock):
        out = foo(Path("/path/to/inputs.txt"), bar=(1, 2, 3), value=42)

        assert out is not None
        assert str(out.path) == "/tmp/temp_file_0.vol"

        del out


if __name__ == "__main__":
    test_resolve_proxy()
