from typing import TypeVar, Generic

T = TypeVar("T")


class Resolver(Generic[T]):

    def resolve(self) -> T:
        pass
