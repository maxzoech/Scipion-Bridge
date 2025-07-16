from typing import Callable

registry = {}


def register(resolver: Callable, datatype: type):
    register[datatype] = resolver
