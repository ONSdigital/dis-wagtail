from collections.abc import Sequence
from contextlib import suppress
from typing import Any, ClassVar, Optional, cast

from django.forms.widgets import RadioSelect
from wagtail import blocks
from wagtail.blocks.struct_block import StructValue

from cms.datavis.blocks.chart_options import AspectRatioBlock
from cms.datavis.blocks.table import SimpleTableBlock
from cms.datavis.blocks.utils import TextInputFloatBlock
from cms.datavis.constants import AxisType, HighChartsChartType, HighchartsTheme

AnnotationsList = list[dict[str, Any]]
AnnotationsReturn = tuple[AnnotationsList, AnnotationsList, AnnotationsList]


class BaseVisualisationBlock(blocks.StructBlock):
    # Extra attributes for subclasses
    highcharts_chart_type: ClassVar[HighChartsChartType]
    x_axis_type: ClassVar[AxisType]
    extra_series_attributes: ClassVar[dict[str, Any]]

    # Editable fields
    # Note that static blocks are intended to be overridden with real blocks or
    # None in subclasses. They are included here in order to control the
    # ordering, as StructBlock has no panel support.

    title = blocks.CharBlock()
    subtitle = blocks.CharBlock()
    caption = blocks.CharBlock(required=False)

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

    # X axis
    x_axis = blocks.StructBlock(
        [
            (
                "title",
                blocks.CharBlock(
                    required=False,
                    help_text="Only use axis titles if it is not clear from the title "
                    "and subtitle what the axis represents.",
                ),
            ),
            ("min", TextInputFloatBlock(label="Minimum", required=False)),
            ("max", TextInputFloatBlock(label="Maximum", required=False)),
            (
                "tick_interval_mobile",
                TextInputFloatBlock(label="Tick interval (mobile)", required=False),
            ),
            (
                "tick_interval_desktop",
                TextInputFloatBlock(label="Tick interval (desktop)", required=False),
            ),
        ]
    )

    # Y axis
    y_axis = blocks.StructBlock(
        [
            (
                "title",
                blocks.CharBlock(
                    required=False,
                    help_text="Only use axis titles if it is not clear from the title "
                    "and subtitle what the axis represents.",
                ),
            ),
            ("min", TextInputFloatBlock(label="Minimum", required=False)),
            ("max", TextInputFloatBlock(label="Maximum", required=False)),
            ("tick_interval_mobile", TextInputFloatBlock(label="Tick interval (mobile)", required=False)),
            ("tick_interval_desktop", TextInputFloatBlock(label="Tick interval (desktop)", required=False)),
            ("value_suffix", blocks.CharBlock(required=False)),  # TODO: implement non-stripping charblock for affixes
            ("tooltip_suffix", blocks.CharBlock(required=False)),  # TODO: implement non-stripping charblock for affixes
        ]
    )

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

    class Meta:
        template = "templates/components/streamfield/datavis/base_highcharts_chart_block.html"

    def get_context(self, value: "StructValue", parent_context: Optional[dict[str, Any]] = None) -> dict[str, Any]:
        context: dict[str, Any] = super().get_context(value, parent_context)

        context["chart_config"] = self.get_component_config(value)
        return context

    def get_highcharts_chart_type(self, value: "StructValue") -> str:
        """Chart type may be set by a field, or hardcoded in the subclass."""
        if chart_type := value.get("select_chart_type"):
            return cast(str, chart_type)
        return self.highcharts_chart_type.value

    def get_component_config(self, value: "StructValue") -> dict[str, Any]:
        rows, series = self.get_series_data(value)

        config = {
            "chartType": self.get_highcharts_chart_type(value),
            "theme": value.get("theme"),
            "headingLevel": 3,
            "title": value.get("title"),
            "subtitle": value.get("subtitle"),
            "caption": value.get("caption"),
            "legend": value.get("show_legend", True),
            "xAxis": self.get_x_axis_config(value.get("x_axis"), rows),
            "yAxis": self.get_y_axis_config(value.get("y_axis")),
            "series": series,
            "useStackedLayout": value.get("use_stacked_layout"),
            "download": self.get_download_config(value),
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
        if (max_value := attrs.get("max")) is not None:
            config["max"] = max_value
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
        if (max_value := attrs.get("max")) is not None:
            config["max"] = max_value
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
        # Extract data points, handling None/empty values
        data_points = [r[series_number] if r[series_number] != "" else None for r in rows]

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

    def get_download_config(self, value: "StructValue") -> dict[str, Any]:
        return {
            "title": f"Download: {value['title'][:30]} ... ",  # TODO work on download metadata
            "itemsList": [
                {
                    "text": "Download image (18KB)",
                    "url": "xyz",
                },
                {
                    "text": "Download CSV (25KB)",
                    "url": "xyz",
                },
                {
                    "text": "Download Excel (25KB)",
                    "url": "xyz",
                },
            ],
        }
