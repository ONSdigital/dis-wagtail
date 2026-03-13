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


def user_can_access_asset(
    *,
    request: HttpRequest,
    user: User | AnonymousUser,
    asset: PrivateMediaMixin,
    permission_policy: CollectionOwnershipPermissionPolicy,
) -> bool:
    from cms.bundles.permissions import user_can_preview_bundle_by_id  # pylint: disable=import-outside-toplevel

    if asset.is_public:
        return True

    if user.is_authenticated and permission_policy.user_has_any_permission_for_instance(
        user, ["choose", "add", "change"], asset
    ):
        return True

    preview_data = request.get_signed_cookie(
        settings.BUNDLE_PREVIEW_COOKIE_NAME,
        default=None,
        salt=f"previewer-{request.user.pk}",
        max_age=settings.BUNDLE_PREVIEW_COOKIE_MAX_AGE,
    )
    if preview_data is None:
        return False

    preview_data = json.loads(preview_data)

    # the user can access the given asset if:
    # - they can preview the bundle the page is in
    # - and the given page
    #   - references the asset via the reference index, or
    #   - the given asset is used by the page, the page is live, but also has unpublished changes.
    #     Once a page is live, the reference index is only updated on publication,
    #     so any unpublished draft would not be tracked.
    if not user_can_preview_bundle_by_id(user, preview_data["bundle"]):
        return False

    in_referencing_page = (
        ReferenceIndex.objects.filter(
            base_content_type__model=Page._meta.model_name.lower(),
            base_content_type__app_label=Page._meta.app_label.lower(),
            to_content_type__model=asset._meta.model_name.lower(),  # type: ignore[union-attr]
            to_content_type__app_label=asset._meta.app_label.lower(),
            to_object_id=asset.pk,
        )
        .annotate(page_id=Cast("object_id", output_field=IntegerField()))
        .filter(page_id=preview_data["page"])
        .exists()
    )
    if in_referencing_page:
        return True

    can_access = False
    if page := Page.objects.filter(pk=preview_data["page"]).first():
        # We want to check the latest revision. This will return the specific instance too
        page = page.get_latest_revision_as_object()
        can_access = str(asset.pk) in page.get_referenced_asset_ids(asset.__class__)

    return can_access
