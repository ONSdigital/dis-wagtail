import json
from functools import partial
from typing import Any

from jinja2 import ChainableUndefined


def undefined_json_handler(obj: Any) -> Any:
    """Custom JSON handler that can handle Nunjucks's ChainableUndefined objects."""
    if isinstance(obj, ChainableUndefined):
        return None
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")


custom_json_dumps = partial(json.dumps, default=undefined_json_handler)
