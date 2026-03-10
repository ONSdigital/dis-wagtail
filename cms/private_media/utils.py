import json
from functools import cache
from typing import TYPE_CHECKING, Any

from django.apps import apps
from django.conf import settings
from django.db.models import IntegerField
from django.db.models.functions import Cast
from wagtail.models import Page, ReferenceIndex

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


def user_can_access_private_asset(
    request: HttpRequest,
    user: User | AnonymousUser,
    asset: type[PrivateMediaMixin],
    permission_policy: CollectionOwnershipPermissionPolicy,
) -> bool:
    if not asset.is_private:  # type: ignore[truthy-function]
        return True
    if permission_policy.user_has_any_permission_for_instance(user, ["choose", "add", "change"], asset):
        return True

    preview_data = request.get_signed_cookie("bundle-preview", False, salt=f"previewer-{request.user.pk}", max_age=30)
    if not preview_data:
        return False

    from cms.bundles.permissions import user_can_preview_bundle_by_id  # pylint: disable=import-outside-toplevel

    preview_data = json.loads(preview_data)

    in_referencing_pages = (
        ReferenceIndex.objects.filter(
            base_content_type__model="page",
            base_content_type__app_label="wagtailcore",
            to_content_type__model=asset._meta.model_name.lower(),  # type: ignore[union-attr]
            to_content_type__app_label=asset._meta.app_label.lower(),
            to_object_id=asset.pk,
        )
        .annotate(page_id=Cast("object_id", output_field=IntegerField()))
        .filter(page_id=preview_data["page"])
        .exists()
    )

    page_is_live = Page.objects.filter(pk=preview_data["page"], live=True, has_unpublished_changes=True).exists()

    # the user can access the given asset if:
    # - they can preview the bundle the page is in
    # - and the given page
    #   - references the asset, or
    #   - the page is live, but also has unpublished changes. Once a page is live,
    #     the reference index is only updated on publication, so any unpublished draft would not be tracked.
    return (in_referencing_pages or page_is_live) and user_can_preview_bundle_by_id(user, preview_data["bundle"])
