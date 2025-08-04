def str_to_bool(bool_string: str) -> bool:
    """Takes a string argument which indicates a boolean, and returns the corresponding boolean value.
    raises ValueError if input string is not one of the recognized boolean like values.
    """
    if bool_string.lower() in ("yes", "true", "t", "y", "1"):
        return True
    if bool_string.lower() in ("no", "false", "f", "n", "0"):
        return False
    raise ValueError(f"Invalid input: {bool_string}")


def require_request(requests, predicate, description):
    """Return the first request matching predicate or raise AssertionError."""
    reqs = list(requests)
    for req in reqs:
        if predicate(req):
            return req

    # Build a short sample of what was seen to aid debugging
    sample = ", ".join(f"{getattr(r, 'method', '?')} {getattr(r, 'url', '?')}" for r in reqs)
    total = len(reqs)

    raise AssertionError(
        f"No request matching {description} was captured "
        f"(checked {total} request{'s' if total != 1 else ''}; sample: {sample})"
    )
