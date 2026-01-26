import json
import logging
from typing import TYPE_CHECKING

from django.core.exceptions import PermissionDenied
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from django.views import View
from wagtail.admin.auth import user_has_any_page_permission, user_passes_test
from wagtail.log_actions import log
from wagtail.models import Page, Revision

from cms.articles.utils import create_data_csv_download_response_from_data
from cms.bundles.mixins import BundledPageMixin
from cms.bundles.permissions import get_bundle_permission, user_can_preview_bundle
from cms.workflows.utils import is_page_ready_to_preview

if TYPE_CHECKING:
    from django.http import HttpRequest

    from cms.users.models import User

logger = logging.getLogger(__name__)


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


def get_csv_data_from_chart(revision_page: Page, chart_id: str) -> tuple[list[list[str | int | float]], str]:
    """Extract CSV data and title from chart.

    Args:
        revision_page: The page object containing the chart.
        chart_id: The unique block ID of the chart.

    Returns:
        A tuple of (data, title) where data is a 2D list for CSV export.

    Raises:
        Http404: If chart not found or data is malformed.
    """
    chart_data = revision_page.get_chart(chart_id)
    if not chart_data:
        raise Http404
    try:
        data = json.loads(chart_data["table"]["table_data"])["data"]
    except (KeyError, json.JSONDecodeError) as e:
        logger.warning(
            "Failed to parse chart data: %s",
            e,
            extra={"chart_id": chart_id, "page_id": revision_page.id, "page_slug": revision_page.slug},
        )
        raise Http404 from e
    return data, chart_data.get("title", "chart")


def get_csv_data_from_table(revision_page: Page, table_id: str) -> tuple[list[list[str | int | float]], str]:
    """Extract CSV data and title from table.

    Args:
        revision_page: The page object containing the table.
        table_id: The unique block ID of the table.

    Returns:
        A tuple of (data, title) where data is a 2D list for CSV export.

    Raises:
        Http404: If table not found or data extraction fails.
    """
    try:
        csv_data = revision_page.get_table_data_for_csv(table_id)
    except ValueError as e:
        logger.warning(
            "Failed to extract table data: %s",
            e,
            extra={"table_id": table_id, "page_id": revision_page.id, "page_slug": revision_page.slug},
        )
        raise Http404 from e
    table_data = revision_page.get_table(table_id)
    title = table_data.get("title") or table_data.get("caption") or "table"
    return csv_data, title


@method_decorator(user_passes_test(user_can_access_csv_download), name="dispatch")
class RevisionChartDownloadView(View):
    """Admin view to download chart data from a page revision.

    This allows downloading chart CSVs from draft/unpublished content during preview.
    Uses the same permission model as Wagtail's revision views.
    """

    def get(self, request: HttpRequest, page_id: int, revision_id: int, chart_id: str) -> HttpResponse:
        """Handle GET request for chart download.

        Args:
            request: The HTTP request.
            page_id: The page ID.
            revision_id: The revision ID.
            chart_id: The chart block ID.

        Returns:
            CSV file download response.

        Raises:
            Http404: If chart not found or data is invalid.
        """
        revision_page = get_revision_page_for_request(request, page_id, revision_id)
        csv_data, title = get_csv_data_from_chart(revision_page, chart_id)

        log(
            action="content.chart_download",
            instance=revision_page,
            data={
                "chart_id": chart_id,
                "revision_id": revision_id,
            },
        )
        return create_data_csv_download_response_from_data(csv_data, title=title)


@method_decorator(user_passes_test(user_can_access_csv_download), name="dispatch")
class RevisionTableDownloadView(View):
    """Admin view to download table data from a page revision.

    This allows downloading table CSVs from draft/unpublished content during preview.
    Uses the same permission model as Wagtail's revision views.
    """

    def get(self, request: HttpRequest, page_id: int, revision_id: int, table_id: str) -> HttpResponse:
        """Handle GET request for table download.

        Args:
            request: The HTTP request.
            page_id: The page ID.
            revision_id: The revision ID.
            table_id: The table block ID.

        Returns:
            CSV file download response.

        Raises:
            Http404: If table not found or data extraction fails.
        """
        revision_page = get_revision_page_for_request(request, page_id, revision_id)
        csv_data, title = get_csv_data_from_table(revision_page, table_id)

        log(
            action="content.table_download",
            instance=revision_page,
            data={
                "table_id": table_id,
                "revision_id": revision_id,
            },
        )
        return create_data_csv_download_response_from_data(csv_data, title=title)
