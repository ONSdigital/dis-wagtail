from collections.abc import Sequence
from contextlib import suppress
from typing import TYPE_CHECKING, Any, ClassVar, Optional, cast

from django.conf import settings
from django.forms.widgets import RadioSelect
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from wagtail import blocks
from wagtail.blocks.struct_block import StructValue

from cms.datavis.blocks.chart_options import AspectRatioBlock
from cms.datavis.blocks.table import SimpleTableBlock
from cms.datavis.blocks.utils import get_approximate_file_size_in_kb
from cms.datavis.constants import AxisType, HighChartsChartType, HighchartsTheme

if TYPE_CHECKING:
    from django.http import HttpRequest
    from django.utils.functional import _StrOrPromise

    from cms.core.models import BasePage


AnnotationsList = list[dict[str, Any]]
AnnotationsReturn = tuple[AnnotationsList, AnnotationsList, AnnotationsList]


class BaseVisualisationBlock(blocks.StructBlock):
    title = blocks.CharBlock()
    subtitle = blocks.CharBlock()
    audio_description = blocks.TextBlock(
        required=True, help_text="An overview of what the chart shows for screen readers."
    )
    caption = blocks.CharBlock(required=False)
    footnotes = blocks.RichTextBlock(required=False, features=settings.RICH_TEXT_BASIC)

    class Meta:
        template = "templates/components/streamfield/datavis/base_highcharts_chart_block.html"


class BaseChartBlock(BaseVisualisationBlock):
    # Extra attributes for subclasses
    highcharts_chart_type: ClassVar[HighChartsChartType]
    x_axis_type: ClassVar[AxisType]
    extra_series_attributes: ClassVar[dict[str, Any]]

    # Editable fields
    # Note that static blocks are intended to be overridden with real blocks or
    # None in subclasses. They are included here in order to control the
    # ordering, as StructBlock has no panel support.
    table = SimpleTableBlock(label="Data table")

    # Override select_chart_type as a ChoiceBlock in subclasses which have
    # options, or override as None, and set highcharts_chart_type as a
    # HighChartsChartType enum instead.
    select_chart_type = blocks.StaticBlock()

    theme = blocks.ChoiceBlock(
        choices=HighchartsTheme.choices,
        default=HighchartsTheme.PRIMARY,
        widget=RadioSelect,
    )
    show_legend = blocks.BooleanBlock(default=True, required=False)
    show_data_labels = blocks.StaticBlock()
    use_stacked_layout = blocks.StaticBlock()
    show_markers = blocks.BooleanBlock(
        default=False,
        required=False,
        help_text="For line charts, markers are always shown at the end of each line. "
        "Only add markers to other data points if the data is uneven, i.e. time "
        "periods missing.",
    )

    # Always define axes in subclasses
    x_axis = blocks.StaticBlock()
    y_axis = blocks.StaticBlock()

    DESKTOP_ASPECT_RATIO = "desktop_aspect_ratio"
    MOBILE_ASPECT_RATIO = "mobile_aspect_ratio"
    options_key_map: ClassVar[dict[str, str]] = {
        # A dict to map our block types to the Design System macro options
        DESKTOP_ASPECT_RATIO: "percentageHeightDesktop",
        MOBILE_ASPECT_RATIO: "percentageHeightMobile",
    }
    options = blocks.StreamBlock(
        [
            (
                DESKTOP_ASPECT_RATIO,
                AspectRatioBlock(
                    required=False,
                    help_text='Remove this option, or set "Default", to use the default aspect ratio for desktop.',
                    widget=RadioSelect(),
                ),
            ),
            (
                MOBILE_ASPECT_RATIO,
                AspectRatioBlock(
                    required=False,
                    help_text='Remove this option, or set "Default", to use the default aspect ratio for mobile.',
                    widget=RadioSelect(),
                ),
            ),
        ],
        block_counts={
            DESKTOP_ASPECT_RATIO: {"max_num": 1},
            MOBILE_ASPECT_RATIO: {"max_num": 1},
        },
        help_text="Additional settings for the chart",
        required=False,
    )

    series_customisation = blocks.StaticBlock()

    def get_context(self, value: "StructValue", parent_context: Optional[dict[str, Any]] = None) -> dict[str, Any]:
        context: dict[str, Any] = super().get_context(value, parent_context)

        context["chart_config"] = self.get_component_config(
            value, parent_context=parent_context, block_id=context.get("block_id")
        )
        return context

    def get_highcharts_chart_type(self, value: "StructValue") -> str:
        """Chart type may be set by a field, or hardcoded in the subclass."""
        if chart_type := value.get("select_chart_type"):
            return cast(str, chart_type)
        return self.highcharts_chart_type.value

    def get_component_config(
        self,
        value: "StructValue",
        *,
        parent_context: Optional[dict[str, Any]] = None,
        block_id: Optional[str] = None,
    ) -> dict[str, Any]:
        rows, series = self.get_series_data(value)

        config = {
            "chartType": self.get_highcharts_chart_type(value),
            "theme": value.get("theme"),
            "headingLevel": 3,
            "description": value.get("audio_description"),
            "title": value.get("title"),
            "subtitle": value.get("subtitle"),
            "caption": value.get("caption"),
            "legend": value.get("show_legend", True),
            "xAxis": self.get_x_axis_config(value.get("x_axis"), rows),
            "yAxis": self.get_y_axis_config(value.get("y_axis")),
            "series": series,
            "useStackedLayout": value.get("use_stacked_layout"),
            "download": self.get_download_config(
                value,
                parent_context=parent_context,
                block_id=block_id,
                rows=rows,
            ),
            "footnotes": self.get_footnotes_config(value),
        }

        point_annotations, range_annotations, line_annotations = self.get_annotations_config(value)
        if point_annotations:
            config["annotations"] = point_annotations
        if range_annotations:
            config["rangeAnnotations"] = range_annotations
        if line_annotations:
            config["referenceLineAnnotations"] = line_annotations

        config.update(self.get_additional_options(value))
        return config

    def get_x_axis_config(
        self,
        attrs: "StructValue",
        rows: Sequence[list[str | int | float]],
    ) -> dict[str, Any]:
        config: dict[str, Any] = {
            "type": self.x_axis_type.value,
        }

        if self.x_axis_type == AxisType.CATEGORICAL:
            config["categories"] = [r[0] for r in rows]

        # Only add x-axis title if supported and provided, as the Highcharts
        # x-axis title default value is undefined. See
        # https://api.highcharts.com/highcharts/xAxis.title.text
        if title := attrs.get("title"):
            config["title"] = title

        if (tick_interval_mobile := attrs.get("tick_interval_mobile")) is not None:
            config["tickIntervalMobile"] = tick_interval_mobile
        if (tick_interval_desktop := attrs.get("tick_interval_desktop")) is not None:
            config["tickIntervalDesktop"] = tick_interval_desktop
        if (min_value := attrs.get("min")) is not None:
            config["min"] = min_value
        if (start_on_tick := attrs.get("start_on_tick")) is not None:
            config["startOnTick"] = start_on_tick
        if (max_value := attrs.get("max")) is not None:
            config["max"] = max_value
        if (end_on_tick := attrs.get("end_on_tick")) is not None:
            config["endOnTick"] = end_on_tick
        return config

    def get_y_axis_config(
        self,
        attrs: "StructValue",
    ) -> dict[str, Any]:
        config = {}

        # Only add y-axis title if supported
        if (title := attrs.get("title")) is not None:
            # Highcharts y-axis title default value is "Values". Set to undefined to
            # disable. See https://api.highcharts.com/highcharts/yAxis.title.text
            config["title"] = title or None

        if (tick_interval_mobile := attrs.get("tick_interval_mobile")) is not None:
            config["tickIntervalMobile"] = tick_interval_mobile
        if (tick_interval_desktop := attrs.get("tick_interval_desktop")) is not None:
            config["tickIntervalDesktop"] = tick_interval_desktop
        if (value_suffix := attrs.get("value_suffix")) is not None:
            config["labels"] = {
                "format": "{value} " + value_suffix,
            }
        if (min_value := attrs.get("min")) is not None:
            config["min"] = min_value
        if (start_on_tick := attrs.get("start_on_tick")) is not None:
            config["startOnTick"] = start_on_tick
        if (max_value := attrs.get("max")) is not None:
            config["max"] = max_value
        if (end_on_tick := attrs.get("end_on_tick")) is not None:
            config["endOnTick"] = end_on_tick
        if (custom_reference_line := attrs.get("custom_reference_line")) is not None:
            config["customReferenceLineValue"] = custom_reference_line
        return config

    def get_annotations_config(self, value: "StructValue") -> AnnotationsReturn:
        annotations_values: AnnotationsList = []
        range_annotations_values: AnnotationsList = []
        line_annotations_values: AnnotationsList = []

        for item in value.get("annotations", []):
            config = item.value.get_config()
            match item.block_type:
                case "point":
                    annotations_values.append(config)
                case "range":
                    range_annotations_values.append(config)
                case "reference_line":
                    line_annotations_values.append(config)
                case _:
                    raise ValueError(f"Unknown annotation type: {item.block_type}")

        return annotations_values, range_annotations_values, line_annotations_values

    def get_series_data(
        self,
        value: "StructValue",
    ) -> tuple[list[list[str | int | float]], list[dict[str, Any]]]:
        headers: list[str] = value["table"].headers
        rows: list[list[str | int | float]] = value["table"].rows
        series = []

        for series_number, series_name in enumerate(headers[1:], start=1):
            series.append(self.get_series_item(value, series_number, series_name, rows))
        return rows, series

    def get_series_item(
        self, value: "StructValue", series_number: int, series_name: str, rows: list[list[str | int | float]]
    ) -> dict[str, Any]:
        """Get the configuration for a single series."""
        data_points = [r[series_number] or None for r in rows]

        item = {
            "name": series_name,
            "data": data_points,
            "animation": False,
        }

        if value.get("show_markers") is not None:
            item["marker"] = value.get("show_markers")
        # Allow subclasses to specify additional parameters for each series
        for key, val in self.get_extra_series_attributes(value, series_number).items():
            item[key] = val
        if tooltip_suffix := value["y_axis"].get("tooltip_suffix"):
            item["tooltip"] = {
                "valueSuffix": tooltip_suffix,
            }
        return item

    def get_extra_series_attributes(self, value: "StructValue", series_number: int) -> dict[str, Any]:
        """Get additional parameters for a specific series."""
        # Start with the default parameters for this chart type
        extra_series_attributes = getattr(self, "extra_series_attributes", {})
        with suppress(AttributeError):
            # Check for per-series customisation
            extra_series_attributes.update(self.get_series_customisation(value, series_number))

        return extra_series_attributes

    def get_additional_options(self, value: "StructValue") -> dict[str, Any]:
        """Get additional global options for the chart."""
        options = {}
        for option in value.get("options", []):
            key = self.options_key_map[option.block_type]
            options[key] = option.value

        return options

    @staticmethod
    def _get_image_download_item() -> dict[str, str]:
        # Placeholder for future image download implementation
        return {
            "text": "Download image (18KB)",
            "url": "xyz",
        }

    def _get_csv_download_item(
        self,
        *,
        parent_context: Optional[dict[str, Any]] = None,
        block_id: Optional[str] = None,
        rows: Optional[list[list[str | int | float]]] = None,
    ) -> Optional[dict[str, str]]:
        # CSV download - only include if we have a valid URL
        if not (parent_context and block_id):
            # Check separately to placate mypy
            return None
        page: Optional[BasePage] = parent_context.get("page")
        if not page:
            return None
        suffix = f" ({get_approximate_file_size_in_kb(rows or [])})"
        request: Optional[HttpRequest] = parent_context.get("request")
        is_preview = getattr(request, "is_preview", False) if request else False

        if is_preview:
            csv_url = self._build_preview_chart_download_url(page, block_id, request)
        else:
            superseded_version: Optional[int] = parent_context.get("superseded_version")
            csv_url = self._build_chart_download_url(page, block_id, superseded_version)

        return {
            "text": f"Download CSV{suffix}",
            "url": csv_url,
        }

    def get_download_config(
        self,
        value: "StructValue",
        *,
        parent_context: Optional[dict[str, Any]] = None,
        block_id: Optional[str] = None,
        rows: Optional[list[list[str | int | float]]] = None,
    ) -> dict[str, Any]:
        items_list: list[dict[str, str]] = []
        items_list.append(self._get_image_download_item())
        if csv_item := self._get_csv_download_item(parent_context=parent_context, block_id=block_id, rows=rows):
            items_list.append(csv_item)

        return {
            "title": f"Download: {value['title']}",
            "itemsList": items_list,
        }

    @staticmethod
    def _build_chart_download_url(page: "BasePage", block_id: str, superseded_version: Optional[int] = None) -> str:
        """Build the chart download URL, handling versioned pages.

        Args:
            page: The page containing the chart.
            block_id: The unique block ID of the chart.
            superseded_version: If viewing a superseded version, the version number.

        Returns:
            The URL to download the chart data as CSV.
        """
        base_url = page.url.rstrip("/")
        version_part = ""

        if superseded_version is not None:
            version_part = f"/versions/{superseded_version}"

        return f"{base_url}{version_part}/download-chart/{block_id}"

    @staticmethod
    def _build_preview_chart_download_url(
        page: "BasePage", block_id: str, request: Optional["HttpRequest"] = None
    ) -> str:
        """Build the chart download URL for preview mode.

        In preview mode, we need to use an admin URL that can access the draft revision.

        Args:
            page: The page containing the chart.
            block_id: The unique block ID of the chart.
            request: The HTTP request object (used to get revision_id from resolver_match).

        Returns:
            The admin URL to download the chart data as CSV, or "#" if unable to build URL.
        """
        # Try to get the revision_id from the request's resolver_match
        revision_id = None
        if request and hasattr(request, "resolver_match") and request.resolver_match:
            revision_id = request.resolver_match.kwargs.get("revision_id")

        # Fall back to the page's latest revision if not available from URL
        if revision_id is None and hasattr(page, "latest_revision_id"):
            revision_id = page.latest_revision_id

        if revision_id is None:
            # Cannot build preview URL without a revision ID
            return "#"

        return reverse(
            "articles:revision_chart_download",
            kwargs={"page_id": page.pk, "revision_id": revision_id, "chart_id": block_id},
        )

    def get_footnotes_config(self, value: "StructValue") -> dict["_StrOrPromise", Any]:
        if footnotes := value.get("footnotes"):
            return {"title": _("Footnotes"), "content": str(footnotes)}
        return {}
