from collections.abc import Sequence
from contextlib import suppress
from typing import TYPE_CHECKING, Any, ClassVar, cast

from django.conf import settings
from django.forms import Media
from django.forms.widgets import RadioSelect
from django.urls import reverse
from django.utils.functional import cached_property
from django.utils.html import strip_tags
from django.utils.translation import gettext_lazy as _
from wagtail import blocks
from wagtail.admin.telepath import register
from wagtail.blocks.struct_block import StructBlockAdapter, StructValue

from cms.core.analytics_utils import get_gtm_attributes_file_download
from cms.core.utils import format_file_size_kb
from cms.data_downloads.utils import get_csv_download_filename
from cms.datavis.blocks.chart_options import AspectRatioBlock
from cms.datavis.blocks.rendered_chart_image import RenderedChartImageChooserBlock
from cms.datavis.blocks.table import SimpleTableBlock
from cms.datavis.blocks.utils import get_approximate_file_size_in_kb
from cms.datavis.constants import AxisType, HighChartsChartType, HighchartsTheme

if TYPE_CHECKING:
    from django.http import HttpRequest

    from cms.core.models import BasePage


AnnotationsList = list[dict[str, Any]]
AnnotationsReturn = tuple[AnnotationsList, AnnotationsList, AnnotationsList]


class BaseVisualisationBlock(blocks.StructBlock):
    figure_number = blocks.CharBlock(required=False, help_text="Include a label for the figure, for example Figure 1.")
    title = blocks.CharBlock(required_on_save=True)
    subtitle = blocks.CharBlock(required=False)
    audio_description = blocks.TextBlock(
        required=True,
        required_on_save=True,
        help_text="An overview of what the chart shows for screen reader users.",
        label="Accessible description",
    )
    caption = blocks.CharBlock(required=False, label="Source text")
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
        required_on_save=True,
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

    # Hidden field populated by the chart render pipeline; see RenderedChartImageChooserBlock
    # and the tamper-protection form mixin in cms.core.forms for why it must stay off-form.
    rendered_chart_image = RenderedChartImageChooserBlock(required=False)

    def get_context(self, value: StructValue, parent_context: dict[str, Any] | None = None) -> dict[str, Any]:
        context: dict[str, Any] = super().get_context(value, parent_context)

        chart_config = self.get_component_config(value, parent_context=parent_context, block_id=context.get("block_id"))
        # Image added here rather than in get_component_config, since get_export_config reuses that
        # method to build the chart exporter API payload: including the rendered image's own
        # URL there would make the config self-referential, changing on every render and
        # defeating the config_hash idempotency check.
        if rendered_chart_image := value.get("rendered_chart_image"):
            chart_config["fallbackImageUrl"] = rendered_chart_image.url
        context["chart_config"] = chart_config
        return context

    def get_highcharts_chart_type(self, value: StructValue) -> str:
        """Chart type may be set by a field, or hardcoded in the subclass."""
        if chart_type := value.get("select_chart_type"):
            return cast(str, chart_type)
        return self.highcharts_chart_type.value

    def get_component_config(
        self,
        value: StructValue,
        *,
        parent_context: dict[str, Any] | None = None,
        block_id: str | None = None,
    ) -> dict[str, Any]:
        rows, series = self.get_series_data(value)

        config = {
            "chartType": self.get_highcharts_chart_type(value),
            "theme": value.get("theme"),
            "headingLevel": 3,
            "description": value.get("audio_description"),
            "figureNumber": value.get("figure_number"),
            "title": value.get("title"),
            "subtitle": value.get("subtitle"),
            "caption": _("Source") + ": " + value.get("caption") if value.get("caption") else None,
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
        }

        # Check for meaningful text before displaying footnotes
        if (footnotes := value.get("footnotes")) and strip_tags(str(footnotes)).strip():
            config["footnotes"] = {
                "title": _("Footnotes"),
                "content": str(footnotes),
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

    def get_export_config(self, value: StructValue) -> dict[str, Any]:
        """Build the chart config sent to the chart exporter API."""
        config = self.get_component_config(value)
        del config["download"]
        config["caption"] = value.get("caption") or None
        return config

    def get_x_axis_config(
        self,
        attrs: StructValue,
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
        attrs: StructValue,
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

    def get_annotations_config(self, value: StructValue) -> AnnotationsReturn:
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
        value: StructValue,
    ) -> tuple[list[list[str | int | float]], list[dict[str, Any]]]:
        headers: list[str] = value["table"].headers
        rows: list[list[str | int | float]] = value["table"].rows
        series = []

        for series_number, series_name in enumerate(headers[1:], start=1):
            series.append(self.get_series_item(value, series_number, series_name, rows))
        return rows, series

    def get_series_item(
        self, value: StructValue, series_number: int, series_name: str, rows: list[list[str | int | float]]
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

    def get_extra_series_attributes(self, value: StructValue, series_number: int) -> dict[str, Any]:
        """Get additional parameters for a specific series."""
        # Start with the default parameters for this chart type
        extra_series_attributes = getattr(self, "extra_series_attributes", {})
        with suppress(AttributeError):
            # Check for per-series customisation
            extra_series_attributes.update(self.get_series_customisation(value, series_number))

        return extra_series_attributes

    def get_additional_options(self, value: StructValue) -> dict[str, Any]:
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
        value: StructValue,
        parent_context: dict[str, Any] | None = None,
        block_id: str | None = None,
        rows: list[list[str | int | float]] | None = None,
    ) -> dict[str, Any] | None:
        # CSV download - only include if we have a valid URL
        if not (parent_context and block_id):
            # Check separately to placate mypy
            return None
        page: BasePage | None = parent_context.get("page")
        if not page:
            return None

        size_suffix = f"({get_approximate_file_size_in_kb(rows or [])})"
        file_size_kb = format_file_size_kb(len(bytes(str(rows or []), "utf-8")))

        request: HttpRequest | None = parent_context.get("request")
        is_preview = getattr(request, "is_preview", False) if request else False

        if is_preview:
            csv_url = self._build_preview_chart_download_url(page, block_id, request)
        else:
            superseded_version: int | None = parent_context.get("superseded_version")
            csv_url = self._build_chart_download_url(page, block_id, superseded_version)

        link_text = _("Download CSV %(size)s") % {"size": size_suffix}
        absolute_csv_url = request.build_absolute_uri(csv_url) if request and not is_preview else csv_url

        return {
            "text": link_text,
            "url": csv_url,
            "attributes": self._get_gtm_attributes_csv_download(link_text, absolute_csv_url, file_size_kb, value),
        }

    def _get_gtm_attributes_csv_download(
        self, text: str, url: str, file_size: str, value: StructValue
    ) -> dict[str, str]:
        file_name = get_csv_download_filename(title=value.get("title"), fallback_stem="chart")
        return {
            **get_gtm_attributes_file_download(
                text=text, url=url, file_extension="csv", file_name=file_name, file_size_kb=file_size
            ),
            "data-ga-chart-title": value.get("title"),
            "data-ga-chart-type": self.get_highcharts_chart_type(value),
        }

    def get_download_config(
        self,
        value: StructValue,
        *,
        parent_context: dict[str, Any] | None = None,
        block_id: str | None = None,
        rows: list[list[str | int | float]] | None = None,
    ) -> dict[str, Any]:
        items_list: list[dict[str, Any]] = []
        items_list.append(self._get_image_download_item())
        if csv_item := self._get_csv_download_item(
            value=value,
            parent_context=parent_context,
            block_id=block_id,
            rows=rows,
        ):
            items_list.append(csv_item)

        return {
            "title": f"Download: {value['title']}",
            "itemsList": items_list,
        }

    @staticmethod
    def _build_download_path_fragment(block_id: str, superseded_version: int | None = None) -> str:
        """Build the chart download URL path portion for published pages."""
        version_part = f"/versions/{superseded_version}" if superseded_version is not None else ""
        return f"{version_part}/download-chart/{block_id}"

    @staticmethod
    def _build_chart_download_url(page: BasePage, block_id: str, superseded_version: int | None = None) -> str:
        """Build the chart download URL, handling versioned pages.

        Args:
            page: The page containing the chart.
            block_id: The unique block ID of the chart.
            superseded_version: If viewing a superseded version, the version number.

        Returns:
            The URL to download the chart data as CSV.
        """
        base_url = page.url.rstrip("/")
        download_fragment = BaseChartBlock._build_download_path_fragment(block_id, superseded_version)
        return f"{base_url}{download_fragment}"

    @staticmethod
    def _build_preview_chart_download_url(page: BasePage, block_id: str, request: HttpRequest | None = None) -> str:
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
            "data_downloads:revision_chart_download",
            kwargs={"page_id": page.pk, "revision_id": revision_id, "chart_id": block_id},
        )


class BaseChartBlockAdapter(StructBlockAdapter):
    """Hides the rendered_chart_image field from the chart block form.

    The field is populated only by the chart render pipeline, not by editors, so it is hidden
    client-side here and any submitted value is discarded server-side (see
    cms.core.forms.PageWithProtectedChartImagesAdminForm). Registering against BaseChartBlock
    covers every chart block subclass, including the Featured* variants.
    """

    js_constructor = "cms.datavis.blocks.base.BaseChartBlock"

    @cached_property
    def media(self) -> Media:
        structblock_media = super().media
        return Media(
            js=[*structblock_media._js, "js/blocks/chart-block.js"],  # pylint: disable=protected-access
            css=structblock_media._css,  # pylint: disable=protected-access
        )


register(BaseChartBlockAdapter(), BaseChartBlock)
