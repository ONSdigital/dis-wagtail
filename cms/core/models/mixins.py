import json
import logging
from collections.abc import Iterator
from typing import TYPE_CHECKING, Any, ClassVar

from django.core.paginator import EmptyPage, Paginator
from django.db import models
from django.http import Http404, HttpResponse
from wagtail.admin.panels import MultiFieldPanel
from wagtail.contrib.routable_page.models import RoutablePageMixin, path
from wagtail.coreutils import WAGTAIL_APPEND_SLASH

from cms.core.utils import create_data_csv_download_response_from_data, flatten_table_data
from cms.datavis.constants import CHART_BLOCK_TYPES, TABLE_BLOCK_TYPES

if TYPE_CHECKING:
    from django.core.paginator import Page
    from django.http import HttpRequest
    from wagtail.admin.panels import Panel
    from wagtail.blocks.stream_block import StreamChild

__all__ = [
    "CSVDownloadMixin",
    "CoreCSVDownloadMixin",
    "ListingFieldsMixin",
    "NoTrailingSlashRoutablePageMixin",
    "SocialFieldsMixin",
    "SubpageMixin",
]

logger = logging.getLogger(__name__)


class ListingFieldsMixin(models.Model):
    """Generic listing fields abstract class to add listing image/text to any new content type easily."""

    listing_image = models.ForeignKey(
        "images.CustomImage",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        help_text="Choose the image you wish to be displayed when this page appears in listings",
    )
    listing_title = models.CharField(
        max_length=255,
        blank=True,
        help_text="Override the page title used when this page appears in listings",
    )
    listing_summary = models.CharField(
        max_length=255,
        blank=True,
        help_text=(
            "The text summary used when this page appears in listings. It’s also used as the "
            "description for search engines if the 'Meta description' field above is not defined."
        ),
    )

    class Meta:
        abstract = True

    promote_panels: ClassVar[list[Panel]] = [
        MultiFieldPanel(
            heading="Listing information",
            children=[
                "listing_image",
                "listing_title",
                "listing_summary",
            ],
        )
    ]


class SocialFieldsMixin(models.Model):
    """Generic social fields abstract class to add social image/text to any new content type easily."""

    social_image = models.ForeignKey(
        "images.CustomImage",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    social_text = models.CharField(max_length=255, blank=True)

    class Meta:
        abstract = True

    promote_panels: ClassVar[list[Panel]] = [
        MultiFieldPanel(
            heading="Social networks",
            children=[
                "social_image",
                "social_text",
            ],
        )
    ]


class SubpageMixin:
    """A helper that provides paginated subpages."""

    PAGE_SIZE = 24

    def get_paginator_page(self, request: HttpRequest) -> Page:
        """Returns the requested page from the list of public and published child pages."""
        children = self.get_children().live().public().specific()  # type: ignore[attr-defined]
        paginator = Paginator(children, per_page=self.PAGE_SIZE)
        try:
            return paginator.page(int(request.GET.get("p", 1)))
        except (EmptyPage, ValueError) as e:
            raise Http404 from e

    def get_context(self, request: HttpRequest, *args: Any, **kwargs: Any) -> dict:
        """Add paginated subpages to the template context."""
        context: dict = super().get_context(request, *args, **kwargs)  # type: ignore[misc]
        context["subpages"] = self.get_paginator_page(request)
        return context


class NoTrailingSlashRoutablePageMixin(RoutablePageMixin):
    """A mixin to remove trailing slashes from RoutablePage routes.
    This ensures that the output of routablepageurl and reverse_subpage does not
    include a trailing slash.
    """

    def reverse_subpage(self, name: str, args: list[str] | None = None, kwargs: dict[str, Any] | None = None) -> str:
        result: str = super().reverse_subpage(name, args, kwargs)
        if not WAGTAIL_APPEND_SLASH:
            result = result.rstrip("/")
        return result


class CoreCSVDownloadMixin:
    """Mixin providing CSV download functionality for pages with CoreStoryBlock content.

    Provides routable endpoints for downloading table data as CSV files.
    Searches for blocks directly in the content stream.

    Requires:
        - The page to have a `content` StreamField using CoreStoryBlock
        - The page to inherit from RoutablePageMixin (or a subclass like NoTrailingSlashRoutablePageMixin)
    """

    def _iter_content_blocks(self) -> Iterator[StreamChild]:
        """Yields content blocks from the page. Override in subclasses for different structures."""
        yield from getattr(self, "content", None) or []

    def _get_block_in_types_by_id(self, block_types: frozenset[str], block_id: str) -> dict[str, Any]:
        """Find a block by its unique block ID for specified block types.

        Args:
            block_types: The frozenset of block types to search within.
            block_id: The unique block ID of the block to find.

        Returns:
            The block's value as a dictionary, or an empty dict if not found.

        Note:
            Block IDs are automatically assigned by Wagtail when content is created
            through the admin interface. Blocks without IDs (e.g., programmatically
            created test data) cannot be retrieved by this method.
        """
        for content_block in self._iter_content_blocks():
            if (
                content_block.block_type in block_types
                and content_block.id is not None
                and str(content_block.id) == block_id
            ):
                return dict(content_block.value)
        return {}

    def get_table(self, table_id: str) -> dict[str, Any]:
        """Finds a table block by its unique block ID in content.

        Args:
            table_id: The unique block ID of the table to find.

        Returns:
            The table block's value as a dictionary, or an empty dict if not found.
        """
        return self._get_block_in_types_by_id(TABLE_BLOCK_TYPES, table_id)

    def get_table_data_for_csv(self, table_id: str) -> list[list[str | int | float]]:
        """Extracts table data in CSV-ready format from TinyTableBlock.

        Flattens structured cell data (headers + rows) into 2D array.
        Extracts only the "value" field from each cell object.

        Args:
            table_id: The unique block ID of the table to extract data from.

        Returns:
            A 2D list of values suitable for CSV export (headers first, then rows).

        Raises:
            ValueError: If table not found or has no data.
        """
        table_data = self.get_table(table_id)
        if not table_data:
            raise ValueError(f"Table with ID {table_id} not found")

        data_dict = table_data.get("data", {})

        # Headers first, then rows - extract only "value" from cell objects
        csv_data = flatten_table_data(data_dict)

        if not csv_data:
            raise ValueError(f"Table {table_id} has no data")
        return csv_data

    @path("download-table/<str:table_id>/")
    def download_table(self, request: HttpRequest, table_id: str) -> HttpResponse:
        """Serves a table download request for a specific table in the page.

        Args:
            request: The HTTP request object.
            table_id: The unique block ID of the table to download.

        Returns:
            An HTTP response with the table CSV download.
        """
        try:
            csv_data = self.get_table_data_for_csv(table_id)
        except ValueError as e:
            logger.warning(
                "Failed to extract table data: %s",
                e,
                extra={
                    "table_id": table_id,
                    "page_id": self.id,  # type: ignore[attr-defined]
                    "page_slug": self.slug,  # type: ignore[attr-defined]
                },
            )
            raise Http404 from e
        table_data = self.get_table(table_id)
        title = table_data.get("title") or table_data.get("caption") or "table"
        return create_data_csv_download_response_from_data(csv_data, title=title)


class CSVDownloadMixin(CoreCSVDownloadMixin):
    """Mixin providing CSV download functionality for pages with SectionStoryBlock content.

    Extends CoreCSVDownloadMixin to search for blocks within sections, and adds chart download support.

    Requires:
        - The page to have a `content` StreamField using SectionStoryBlock
        - The page to inherit from RoutablePageMixin (or a subclass like NoTrailingSlashRoutablePageMixin)
    """

    def _iter_content_blocks(self) -> Iterator[StreamChild]:
        """Yields content blocks from within sections."""
        for section_block in getattr(self, "content", None) or []:
            if section_block.block_type != "section":
                continue
            yield from section_block.value.get("content", [])

    def get_chart(self, chart_id: str) -> dict[str, Any]:
        """Finds a chart block by its unique block ID in content sections.

        Args:
            chart_id: The unique block ID of the chart to find

        Returns:
            The chart block's value as a dictionary, or an empty dict if not found.
        """
        return self._get_block_in_types_by_id(CHART_BLOCK_TYPES, chart_id)

    @path("download-chart/<str:chart_id>/")
    def download_chart(self, request: HttpRequest, chart_id: str) -> HttpResponse:
        """Serves a chart download request for a specific chart in the page.

        Args:
            request: The HTTP request object.
            chart_id: The unique block ID of the chart to download.

        Returns:
            An HTTP response with the chart download.
        """
        chart_data = self.get_chart(chart_id)
        if not chart_data:
            raise Http404
        try:
            data = json.loads(chart_data["table"]["table_data"])["data"]
        except (KeyError, json.JSONDecodeError) as e:
            logger.warning(
                "Failed to parse chart data: %s",
                e,
                extra={
                    "chart_id": chart_id,
                    "page_id": self.id,  # type: ignore[attr-defined]
                    "page_slug": self.slug,  # type: ignore[attr-defined]
                },
            )
            raise Http404 from e

        return create_data_csv_download_response_from_data(data, title=chart_data.get("title", "chart"))
