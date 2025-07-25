import os
import pytest
import tempfile
from scipion_bridge.external_call import Domain
from scipion_bridge.utils.environment.cmd_exec import ShellExecProvider
from subprocess import PIPE

PYTHON_DOMAIN = Domain("PY", "python")


def test_shell_exec():

    provider = ShellExecProvider()

    output = provider(
        "python",
        PYTHON_DOMAIN,
        [
            "python",
            "-c",
            '"import sys; sys.exit(0)"',
        ],
        run_args={"shell": True, "stdout": PIPE, "stderr": PIPE},
    )

    assert output == 0

    with pytest.raises(RuntimeError):
        output = provider(
            "python",
            PYTHON_DOMAIN,
            [
                "python",
                "-c",
                '"import sys; sys.exit(42)"',
            ],
            run_args={"shell": True, "stdout": PIPE, "stderr": PIPE},
        )
