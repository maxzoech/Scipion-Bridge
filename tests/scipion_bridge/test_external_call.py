import itertools
from functools import partial

from scipion_bridge.external_call import foreign_function, Domain
from scipion_bridge.utils.environment.container import Container

import pytest
from pytest_mock import MockerFixture

xmipp_domain = Domain("XMIPP", ["scipion", "run"])
xmipp_func = partial(foreign_function, domain=xmipp_domain)


@xmipp_func
def xmipp_to_something(inputs: str, outputs: str, *, keyword_param: int):
    pass


def test_basic_xmipp_func(mocker: MockerFixture):

    container = Container()
    container.wire(modules=[__name__])

    exec_mock = mocker.Mock()

    with container.shell_exec.override(exec_mock):
        xmipp_to_something("/some/input", "/some/output", keyword_param=42)

        exec_mock.assert_called_with(
            "xmipp_to_something",
            xmipp_domain,
            [
                "scipion",
                "run",
                "xmipp_to_something",
                "-inputs",
                "/some/input",
                "-outputs",
                "/some/output",
                "--keyword_param",
                "42",
            ],
            {"shell": True, "stderr": -1},
        )


@partial(xmipp_func, args_map={"inputs": "i", "outputs": "o"})
def xmipp_to_something_with_mapping(inputs: str, outputs: str, *, keyword_param: int):
    pass


def test_basic_xmipp_func_with_mapping(mocker: MockerFixture):

    container = Container()
    container.wire(modules=[__name__])

    exec_mock = mocker.Mock()

    with container.shell_exec.override(exec_mock):
        xmipp_to_something_with_mapping("/some/input", "/some/output", keyword_param=42)

        exec_mock.assert_called_with(
            "xmipp_to_something_with_mapping",
            xmipp_domain,
            [
                "scipion",
                "run",
                "xmipp_to_something_with_mapping",
                "-i",
                "/some/input",
                "-o",
                "/some/output",
                "--keyword_param",
                "42",
            ],
            {"shell": True, "stderr": -1},
        )


def xmipp_boolean(inputs: str, *, boolean_flag: bool):
    pass


@pytest.mark.parametrize(
    "flag,rename_flag", itertools.product([True, False], [True, False])
)
def test_boolean_function(mocker: MockerFixture, flag: bool, rename_flag: bool):
    flag_name = "renamed" if rename_flag else "boolean_flag"
    args_map = (
        {"inputs": "i", "boolean_flag": flag_name} if rename_flag else {"inputs": "i"}
    )

    _xmipp_boolean = xmipp_func(xmipp_boolean, args_map=args_map)

    container = Container()
    container.wire(modules=[__name__])

    exec_mock = mocker.Mock()

    with container.shell_exec.override(exec_mock):
        _xmipp_boolean("/some/input", boolean_flag=flag)

        flag_result = [f"--{flag_name}"] if flag else []

        exec_mock.assert_called_with(
            "xmipp_boolean",
            xmipp_domain,
            [
                "scipion",
                "run",
                "xmipp_boolean",
                "-i",
                "/some/input",
            ]
            + flag_result,
            {"shell": True, "stderr": -1},
        )


def test_function_with_defaults(mocker: MockerFixture):

    @xmipp_func
    def xmipp_func_with_defaults(output="/path/to/output.txt", *, foo: int, value=42):
        pass

    container = Container()
    container.wire(modules=[__name__])

    exec_mock = mocker.Mock()

    with container.shell_exec.override(exec_mock):
        xmipp_func_with_defaults(foo=12)

        exec_mock.assert_called_with(
            "xmipp_func_with_defaults",
            xmipp_domain,
            [
                "scipion",
                "run",
                "xmipp_func_with_defaults",
                "-output",
                "/path/to/output.txt",
                "--foo",
                "12",
                "--value",
                "42",
            ],
            {"shell": True, "stderr": -1},
        )


def xmipp_invalid_func():
    print("Hello world!")


def test_non_empty_function():
    with pytest.raises(RuntimeError):
        xmipp_func(xmipp_invalid_func)

    with pytest.raises(RuntimeError):
        xmipp_func(lambda x: x + 2)  # Just pass an expression which is not allowed


def test_inner_func_definition():
    try:

        @partial(xmipp_func)
        def xmipp_to_something_with_mapping():
            pass

    except IndentationError:
        assert False, "Nested function raised indentation error"


def xmipp_invalid_flag_function(some_flag: bool):
    pass


def test_invalid_boolean_args_definition():
    with pytest.raises(RuntimeError):
        xmipp_func(xmipp_invalid_flag_function)


@partial(
    xmipp_func,
    args_map={"some_argument": "renamed"},
    args_validation={"some_argument": "(.+)\\.vol"},
)
def xmipp_function_with_validation(some_argument: str):
    pass


def test_argument_validation(mocker: MockerFixture):  # , arg_name):
    container = Container()
    container.wire(modules=[__name__])

    exec_mock = mocker.Mock()

    with container.shell_exec.override(exec_mock):
        xmipp_function_with_validation("/some/path/to/file.vol")

        exec_mock.assert_called_with(
            "xmipp_function_with_validation",
            xmipp_domain,
            [
                "scipion",
                "run",
                "xmipp_function_with_validation",
                "-renamed",
                "/some/path/to/file.vol",
            ],
            {"shell": True, "stderr": -1},
        )

        with pytest.raises(ValueError):
            xmipp_function_with_validation("/some/path/to/file.invalid")


@partial(xmipp_func, postprocess_fn=lambda x: [[x[0][1]]] + x[1:])
def xmipp_func_custom_postprocessing(argument: str, *, flag: bool):
    pass


def test_custom_postprocessing(mocker: MockerFixture):
    container = Container()
    container.wire(modules=[__name__])

    exec_mock = mocker.Mock()

    with container.shell_exec.override(exec_mock):
        xmipp_func_custom_postprocessing("/some/path/to/file.vol", flag=True)

        exec_mock.assert_called_with(
            "xmipp_func_custom_postprocessing",
            xmipp_domain,
            [
                "scipion",
                "run",
                "xmipp_func_custom_postprocessing",
                "/some/path/to/file.vol",
                "--flag",
            ],
            {"shell": True, "stderr": -1},
        )
