import contextlib


def numberfy(value: str) -> int | float | str:
    stripped = value.strip()
    if stripped.isdigit():
        return int(stripped)
    with contextlib.suppress(ValueError):
        return float(stripped)
    return value
