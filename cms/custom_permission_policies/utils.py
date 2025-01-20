from functools import cache

from django.apps import apps

from cms.custom_permission_policies.models import MediaChildMixin, MediaParentMixin


@cache
def get_media_child_models() -> list[type[MediaChildMixin]]:
    """Return all registered models that use the `MediaChildMixin` mixin."""
    return [m for m in apps.get_models() if issubclass(m, MediaChildMixin)]


@cache
def get_media_parent_models() -> list[type[MediaParentMixin]]:
    """Return all registered models that use the `MediaParentMixin` mixin."""
    return [m for m in apps.get_models() if issubclass(m, MediaParentMixin)]
