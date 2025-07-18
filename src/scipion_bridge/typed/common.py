from .resolve import resolver


@resolver
def resolve_any_to_str(value: object) -> str:
    return str(value)
