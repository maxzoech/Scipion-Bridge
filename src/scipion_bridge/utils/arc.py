import os
from typing import Dict
import warnings


class FileReferenceCounter:

    def __init__(self) -> None:
        self.references: Dict[os.PathLike, int] = {}

    def add_reference(self, path: os.PathLike):
        if path not in self.references:
            self.references[path] = 1
        else:
            count = self.references[path]
            self.references[path] = count + 1

    def remove_reference(self, path: os.PathLike):
        assert (
            path in self.references
        ), f"Path {path} not managed by automatic reference counting"
        count = self.references[path]

        if count > 1:
            self.references[path] = count - 1
        else:
            del self.references[path]

    def is_tracked(self, path: os.PathLike):
        return path in self.references

    def get_count(self, path: os.PathLike):
        if not self.is_tracked(path):
            warnings.warn(
                "Reference count requested for untracked path {path}; returned 0",
                UserWarning,
            )
            return 0
        else:
            return self.references[path]

    def _print_reference_count(self):
        from tabulate import tabulate

        print(tabulate(self.references.items(), headers=["Path", "Ref. Count"]))


manager = FileReferenceCounter()
