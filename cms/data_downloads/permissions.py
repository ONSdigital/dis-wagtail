from typing import TYPE_CHECKING

from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404
from wagtail.admin.auth import user_has_any_page_permission
from wagtail.models import Page, Revision

from cms.bundles.mixins import BundledPageMixin
from cms.bundles.permissions import get_bundle_permission, user_can_preview_bundle
from cms.workflows.utils import is_page_ready_to_preview

if TYPE_CHECKING:
    from django.http import HttpRequest

    from cms.users.models import User


def user_can_access_csv_download(user: User) -> bool:
    """Check if user can access CSV downloads for charts and tables.

    Allows access for users with page permissions OR bundle view permission.

    Note that a user may still not be able to download a specific CSV
    if they lack permissions on the relevant page or bundle.
    """
    if user_has_any_page_permission(user):
        return True
    # Bundle viewers can also access CSV downloads
    return user.has_perm(get_bundle_permission("view"))


def get_revision_page_for_request(request: HttpRequest, page_id: int, revision_id: int) -> Page:
    """Get the page as it was at the specified revision.

    Args:
        request: The HTTP request.
        page_id: The ID of the page.
        revision_id: The ID of the revision.

    Returns:
        The page object at the specified revision.

    Raises:
        PermissionDenied: If user lacks edit/publish permissions on the page
            or bundle preview permissions.
        Http404: If the page or revision does not exist.
    """
    # Get the page and check permissions
    page = get_object_or_404(Page, id=page_id).specific

    # Check standard Wagtail page permissions
    perms = page.permissions_for_user(request.user)
    has_page_perms = perms.can_edit()

    # Check bundle preview permissions (only if page is bundled)
    has_bundle_preview = False
    if not has_page_perms and isinstance(page, BundledPageMixin) and is_page_ready_to_preview(page):
        has_bundle_preview = any(user_can_preview_bundle(request.user, bundle) for bundle in page.bundles.all())

    if not (has_page_perms or has_bundle_preview):
        raise PermissionDenied

    # Get the revision - use object_id to match the page
    # Revisions use object_id (as string) to reference the page
    revision = get_object_or_404(Revision.page_revisions, id=revision_id, object_id=str(page_id))

    # Get the page as it was at this revision
    return revision.as_object()
