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


def _asset_in_authorized_pages(asset: PrivateMediaMixin, page_ids: list[int]) -> bool:
    """Check if the asset is referenced by any of the given pages."""
    in_referencing_page = (
        ReferenceIndex.objects.filter(
            base_content_type__model=Page._meta.model_name.lower(),
            base_content_type__app_label=Page._meta.app_label.lower(),
            to_content_type__model=asset._meta.model_name.lower(),  # type: ignore[union-attr]
            to_content_type__app_label=asset._meta.app_label.lower(),
            to_object_id=asset.pk,
        )
        .annotate(page_id=Cast("object_id", output_field=IntegerField()))
        .filter(page_id__in=page_ids)
        .exists()
    )
    if in_referencing_page:
        return True

    # Fall back to checking latest revisions for draft content
    for base_page in Page.objects.filter(pk__in=page_ids):
        specific_page = base_page.get_latest_revision_as_object()
        if str(asset.pk) in specific_page.get_referenced_asset_ids(asset.__class__):
            return True

    return False


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

    if settings.IS_EXTERNAL_ENV or not request.user.is_authenticated:
        return False

    if permission_policy.user_has_any_permission_for_instance(user, ["choose", "add", "change"], asset):
        return True

    cookie_data = request.get_signed_cookie(
        settings.BUNDLE_PREVIEW_COOKIE_NAME,
        default=None,
        salt=f"previewer-{request.user.pk}",
        max_age=settings.BUNDLE_PREVIEW_COOKIE_MAX_AGE,
    )

    try:
        parsed = json.loads(cookie_data)
    except (json.JSONDecodeError, TypeError):
        return False

    # The cookie may contain multiple preview entries (one per tab/page) to avoid
    # clobbering when multiple preview tabs are open simultaneously.
    preview_entries: list[dict[str, int]] = parsed if isinstance(parsed, list) else [parsed]

    # Filter to entries where the user can actually preview the bundle
    authorized_page_ids = [
        entry["page"] for entry in preview_entries if user_can_preview_bundle_by_id(user, entry["bundle"])
    ]
    if not authorized_page_ids:
        return False

    # The user can access the given asset if any authorized page:
    #   - references the asset via the reference index, or
    #   - uses the asset in an unpublished draft (the reference index is only
    #     updated on publication, so drafts wouldn't be tracked there).
    return _asset_in_authorized_pages(asset, authorized_page_ids)
