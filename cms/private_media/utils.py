from functools import cache

from django.apps import apps

from cms.private_media.models import PrivateMediaMixin


@cache
def get_private_media_models() -> list[type[PrivateMediaMixin]]:
    """Return all registered models that use the `PrivateMediaMixin` mixin."""
    return [m for m in apps.get_models() if issubclass(m, PrivateMediaMixin)]
