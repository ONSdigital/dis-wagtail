from functools import cache

from django.apps import apps

from cms.private_media.models import MediaParentMixin, ParentDerivedPrivacyMixin


@cache
def get_parent_derived_privacy_models() -> list[type[ParentDerivedPrivacyMixin]]:
    """Return all registered models that use the `ParentDerivedPrivacyMixin` mixin."""
    return [m for m in apps.get_models() if issubclass(m, ParentDerivedPrivacyMixin)]


@cache
def get_media_parent_models() -> list[type[MediaParentMixin]]:
    """Return all registered models that use the `MediaParentMixin` mixin."""
    return [m for m in apps.get_models() if issubclass(m, MediaParentMixin)]
