from functools import cache
from typing import TYPE_CHECKING, Any

from django.apps import apps
from django.conf import settings

if TYPE_CHECKING:
    from cms.private_media.models import PrivateMediaMixin


@cache
def get_private_media_models() -> list[type[PrivateMediaMixin]]:
    """Return all registered models that use the `PrivateMediaMixin` mixin."""
    from cms.private_media.models import PrivateMediaMixin  # pylint: disable=import-outside-toplevel

    return [m for m in apps.get_models() if issubclass(m, PrivateMediaMixin)]


def get_frontend_cache_configuration() -> dict[str, Any]:
    """Return the frontend cache configuration for this project."""
    return getattr(settings, "WAGTAILFRONTENDCACHE", {})
