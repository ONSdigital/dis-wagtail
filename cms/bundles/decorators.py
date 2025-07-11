from collections.abc import Callable
from functools import wraps
from typing import Any

from django.conf import settings


def ons_bundle_api_enabled(func: Callable) -> Callable:
    """Decorator that only executes the function if the ONS_BUNDLE_API_ENABLED
    setting is True.
    """

    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        if not getattr(settings, "ONS_BUNDLE_API_ENABLED", False):
            return None
        return func(*args, **kwargs)

    return wrapper
