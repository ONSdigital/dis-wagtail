import json
from functools import partial
from typing import Any

from jinja2 import ChainableUndefined


def undefined_json_handler(obj: Any) -> Any:
    """Custom JSON handler that can handle Nunjucks's ChainableUndefined objects.

    Python documentation, showing an example use of this pattern, passed as the
    `default` parameter to json.dumps:
    https://docs.python.org/3/library/json.html#:~:text=Specializing%20JSON%20object%20encoding
    """
    if isinstance(obj, ChainableUndefined):
        return None
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")


custom_json_dumps = partial(json.dumps, default=undefined_json_handler)
