import json
from typing import TYPE_CHECKING

from django.core.exceptions import PermissionDenied
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from django.views import View
from wagtail.admin.auth import user_has_any_page_permission, user_passes_test
from wagtail.models import Page, Revision

from cms.articles.utils import create_data_csv_download_response_from_data
from cms.bundles.mixins import BundledPageMixin
from cms.bundles.permissions import get_bundle_permission, user_can_preview_bundle
from cms.workflows.utils import is_page_ready_to_preview

if TYPE_CHECKING:
    from django.http import HttpRequest

    from cms.users.models import User


def user_can_access_chart_download(user: "User") -> bool:
    """Check if user can access chart downloads.

    Allows access for users with page permissions OR bundle view permission.

    Note that a user may still not be able to download a specific chart
    if they lack permissions on the relevant page or bundle.
    """
    if user_has_any_page_permission(user):
        return True
    # Bundle viewers can also access chart downloads
    return user.has_perm(get_bundle_permission("view"))


@method_decorator(user_passes_test(user_can_access_chart_download), name="dispatch")
class RevisionChartDownloadView(View):
    """Admin view to download chart data from a page revision.

    This allows downloading chart CSVs from draft/unpublished content during preview.
    Uses the same permission model as Wagtail's revision views.
    """

    def get(self, request: "HttpRequest", page_id: int, revision_id: int, chart_id: str) -> HttpResponse:
        """Handle GET request for chart download.

        Args:
            request: The HTTP request.
            page_id: The page ID.
            revision_id: The revision ID.
            chart_id: The chart block ID.

        Returns:
            CSV file download response.

        Raises:
            PermissionDenied: If user lacks edit/publish permissions on the page
                or bundle preview permissions.
            Http404: If page, revision, or chart not found.
        """
        # Get the page and check permissions
        page = get_object_or_404(Page, id=page_id).specific

        # Check standard Wagtail page permissions
        perms = page.permissions_for_user(request.user)
        has_page_perms = perms.can_publish() or perms.can_edit()

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
        revision_page = revision.as_object()

        # Get the chart data using the page's get_chart method
        chart_data = revision_page.get_chart(chart_id)
        if not chart_data:
            raise Http404

        try:
            data = json.loads(chart_data["table"]["table_data"])["data"]
        except (KeyError, json.JSONDecodeError) as e:
            raise Http404 from e

        return create_data_csv_download_response_from_data(data, title=chart_data.get("title", "chart"))
