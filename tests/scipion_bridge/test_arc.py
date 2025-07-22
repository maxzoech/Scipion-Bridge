from pathlib import Path
from scipion_bridge.utils.arc import FileReferenceCounter

import pytest


def test_reference_counting():
    manager = FileReferenceCounter()
    path_1 = Path("/path/to/file_1.txt")
    path_2 = Path("/path/to/file_2.txt")

    with pytest.warns(UserWarning):
        assert manager.get_count(path_1) == 0

    manager.add_reference(path_1)
    manager.add_reference(path_1)

    assert manager.get_count(path_1) == 2

    manager.remove_reference(path_1)
    manager.add_reference(path_2)

    assert manager.get_count(path_1) == 1
    assert manager.get_count(path_2) == 1

    manager.remove_reference(path_1)

    with pytest.raises(AssertionError):
        manager.remove_reference(path_1)


if __name__ == "__main__":
    test_reference_counting()
