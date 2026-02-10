def numberfy(value: str) -> int | float | str:
    stripped = value.strip()
    if stripped.isdigit():
        return int(stripped)
    try:
        return float(stripped)
    except ValueError:
        pass
    return value
