import json
import logging
from collections.abc import Iterator
from typing import TYPE_CHECKING, Any

from django.http import Http404, HttpResponse
from wagtail.contrib.routable_page.models import path

from cms.core.blocks import ONSTableBlock
from cms.core.blocks.constants import CHART_BLOCK_TYPES, TABLE_BLOCK_TYPES
from cms.data_downloads.utils import create_data_csv_download_response_from_data, flatten_table_data
from cms.datavis.blocks.base import BaseChartBlock

if TYPE_CHECKING:
    from django.http import HttpRequest
    from wagtail.blocks.stream_block import StreamChild

logger = logging.getLogger(__name__)


class DataDownloadMixin:
    """Mixin providing data download functionality for pages with section-based content.

    Provides routable endpoints for downloading table and chart data as CSV files.
    Searches for blocks within sections in the content stream.

    Requires:
        - The page to have a `content` StreamField with sections (e.g., SectionStoryBlock or CoreStoryBlock)
        - The page to inherit from RoutablePageMixin (or a subclass like NoTrailingSlashRoutablePageMixin)
    """

    def _iter_content_blocks(self) -> Iterator[StreamChild]:
        """Yields content blocks from within sections."""
        for section_block in getattr(self, "content", None) or []:
            if section_block.block_type != "section":
                continue
            yield from section_block.value.get("content", [])

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

    def _get_downloadable_blocks(self) -> list[tuple[str, str]]:
        blocks: list[tuple[str, str]] = []

        for content_block in self._iter_content_blocks():
            if content_block.id is not None and (
                content_block.block_type in TABLE_BLOCK_TYPES or content_block.block_type in CHART_BLOCK_TYPES
            ):
                block_type: str = content_block.block_type
                block_id: str = content_block.id
                blocks.append((block_type, block_id))

        return blocks

    def get_downloadable_block_paths(self) -> list[str]:
        urls: list[str] = []

        path_prefix_len = len(self.url)  # type: ignore[attr-defined]
        for block_type, block_id in self._get_downloadable_blocks():
            url = ""
            if block_type in TABLE_BLOCK_TYPES:
                url = ONSTableBlock._build_table_download_url(self, block_id)  # pylint: disable=protected-access
            elif block_type in CHART_BLOCK_TYPES:
                url = BaseChartBlock._build_chart_download_url(  # pylint: disable=protected-access
                    self,  # type: ignore[arg-type]
                    block_id,
                )
            if url:
                if url.startswith("/"):
                    url = url[path_prefix_len:]
                urls.append(url)

        return urls

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
