from functools import cache
from typing import TYPE_CHECKING, Any

from django.apps import apps
from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.db.models import IntegerField
from django.db.models.functions import Cast
from django.utils import timezone
from wagtail.models import ReferenceIndex

if TYPE_CHECKING:
    from django.contrib.auth.models import AnonymousUser
    from django.http import HttpRequest
    from wagtail.permission_policies.collections import CollectionOwnershipPermissionPolicy

    from cms.private_media.models import PrivateMediaMixin
    from cms.users.models import User


@cache
def get_private_media_models() -> list[type[PrivateMediaMixin]]:
    """Return all registered models that use the `PrivateMediaMixin` mixin."""
    from cms.private_media.models import PrivateMediaMixin  # pylint: disable=import-outside-toplevel

    return [m for m in apps.get_models() if issubclass(m, PrivateMediaMixin)]


def get_frontend_cache_configuration() -> dict[str, Any]:
    """Return the frontend cache configuration for this project."""
    return getattr(settings, "WAGTAILFRONTENDCACHE", {})


def check_user_access_for_private_media(
    request: HttpRequest,
    user: User | AnonymousUser,
    asset: type[PrivateMediaMixin],
    permission_policy: CollectionOwnershipPermissionPolicy,
) -> None:
    if not asset.is_private:  # type: ignore[truthy-function]
        return
    if permission_policy.user_has_any_permission_for_instance(user, ["choose", "add", "change"], asset):
        return

    if not (bundle_preview_data := request.session.get("bundle-preview")):
        raise PermissionDenied

    if bundle_preview_data["timestamp"] < timezone.now().timestamp() - 30:
        raise PermissionDenied

    referencing_pages = (
        ReferenceIndex.objects.filter(
            base_content_type__model="page",
            base_content_type__app_label="wagtailcore",
            to_content_type__model=asset._meta.model_name.lower(),  # type: ignore[union-attr]
            to_content_type__app_label=asset._meta.app_label.lower(),
            to_object_id=asset.pk,
        )
        .annotate(page_id=Cast("object_id", output_field=IntegerField()))
        .values_list("page_id", flat=True)
    )

    from cms.bundles.permissions import user_can_preview_bundle_by_id  # pylint: disable=import-outside-toplevel

    if not (
        bundle_preview_data["page"] in referencing_pages
        and user_can_preview_bundle_by_id(user, bundle_preview_data["bundle"])
    ):
        raise PermissionDenied
