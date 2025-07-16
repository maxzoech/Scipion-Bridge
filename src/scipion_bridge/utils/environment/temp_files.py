import os
import tempfile

import logging


class TemporaryFilesProvider:

    def new_temporary_file(self, suffix: str) -> os.PathLike:
        new_file = tempfile.NamedTemporaryFile(suffix=suffix, delete=False).name
        logging.debug(f"Creating new temporary file at {new_file}")

        return new_file

    def delete(self, path: os.PathLike):
        logging.debug(f"Remove file at {path}")

        os.remove(path)
