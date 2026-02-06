import json
import logging
from typing import TYPE_CHECKING

from django.http import Http404, HttpResponse
from django.utils.decorators import method_decorator
from django.views import View
from wagtail.admin.auth import user_passes_test
from wagtail.models import Page

from cms.data_downloads.permissions import get_revision_page_for_request, user_can_access_csv_download
from cms.data_downloads.utils import create_data_csv_download_response_from_data

if TYPE_CHECKING:
    from django.http import HttpRequest

logger = logging.getLogger(__name__)


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
        return create_data_csv_download_response_from_data(csv_data, title=title)
