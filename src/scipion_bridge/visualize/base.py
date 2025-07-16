from abc import ABC, abstractmethod
from typing import Any


class Visualizer(ABC):

    @abstractmethod
    def show(self, data: Any):
        pass

    @property
    @abstractmethod
    def datatype(self) -> str:
        pass
