from collections.abc import Sequence
from typing import Any, ClassVar, Optional, cast

from django.core.exceptions import ValidationError
from django.forms.widgets import Media, RadioSelect
from django.utils.functional import cached_property
from wagtail import blocks
from wagtail.blocks.struct_block import StructValue

from cms.datavis.blocks.annotations import PointAnnotationBlock
from cms.datavis.blocks.chart_options import AspectRatioBlock
from cms.datavis.blocks.table import SimpleTableBlock
from cms.datavis.blocks.utils import TextInputFloatBlock
from cms.datavis.constants import HighchartsTheme


class BaseVisualisationBlock(blocks.StructBlock):
    # Extra attributes for subclasses
    highcharts_chart_type: ClassVar[str]
    supports_stacked_layout: ClassVar[bool]
    supports_x_axis_title: ClassVar[bool] = False
    supports_y_axis_title: ClassVar[bool] = False
    supports_data_labels: ClassVar[bool]
    supports_markers: ClassVar[bool]
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
    # options, or override as None, and set highcharts_chart_type as a string
    # instead.
    select_chart_type = blocks.StaticBlock()

    theme = blocks.ChoiceBlock(
        choices=HighchartsTheme.choices,
        default=HighchartsTheme.PRIMARY,
        widget=RadioSelect,
    )
    show_legend = blocks.BooleanBlock(default=True, required=False)
    show_data_labels = blocks.StaticBlock()
    use_stacked_layout = blocks.BooleanBlock(default=False, required=False)
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
                "tick_interval",
                TextInputFloatBlock(label="Tick interval", required=False),
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
            ("tick_interval", TextInputFloatBlock(required=False)),
            # TODO: implement non-stripping charblock
            ("value_suffix", blocks.CharBlock(required=False)),
            ("tooltip_suffix", blocks.CharBlock(required=False)),
        ]
    )

    annotations = blocks.StreamBlock(
        [
            ("point", PointAnnotationBlock()),
            # TODO: future implementation will have different block types, and
            # possibly split Point too to cater for continuous vs discrete data
            # ("line", LineAnnotationBlock()),
            # ("area", AreaAnnotationBlock()),
        ],
        required=False,
    )

    desktop_aspect_ratio = "desktop_aspect_ratio"
    mobile_aspect_ratio = "mobile_aspect_ratio"
    options_key_map: ClassVar[dict[str, str]] = {
        desktop_aspect_ratio: "percentageHeightDesktop",
        mobile_aspect_ratio: "percentageHeightMobile",
    }
    options = blocks.StreamBlock(
        [
            (
                desktop_aspect_ratio,
                AspectRatioBlock(
                    required=False,
                    help_text='Remove this option, or set "Default", to use the default aspect ratio for desktop.',
                    widget=RadioSelect(),
                ),
            ),
            (
                mobile_aspect_ratio,
                AspectRatioBlock(
                    required=False,
                    help_text='Remove this option, or set "Default", to use the default aspect ratio for mobile.',
                    widget=RadioSelect(),
                ),
            ),
        ],
        block_counts={
            desktop_aspect_ratio: {"max_num": 1},
            mobile_aspect_ratio: {"max_num": 1},
        },
        help_text="Additional settings for the chart",
        required=False,
    )

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
        return self.highcharts_chart_type

    def get_component_config(self, value: "StructValue") -> dict[str, Any]:
        headers: list[str] = value["table"].headers
        rows: list[list[str | int | float]] = value["table"].rows

        config = {
            "chartType": self.get_highcharts_chart_type(value),
            "theme": value.get("theme"),
            "title": value.get("title"),
            "subtitle": value.get("subtitle"),
            "caption": value.get("caption"),
            "legend": value.get("show_legend", True),
            "xAxis": self.get_x_axis_config(value.get("x_axis"), rows),
            "yAxis": self.get_y_axis_config(value.get("y_axis")),
            "series": self.get_series_data(value, headers, rows),
            "useStackedLayout": value.get("use_stacked_layout"),
            "annotations_values": self.get_annotations_config(value),
            "download": self.get_download_config(value),
        }

        config.update(self.get_additional_options(value))
        return config

    def get_x_axis_config(
        self,
        attrs: "StructValue",
        rows: Sequence[list[str | int | float]],
    ) -> dict[str, Any]:
        config: dict[str, Any] = {
            "type": "category",
            "categories": [r[0] for r in rows],
        }

        # Only add x-axis title if supported and provided, as the Highcharts
        # x-axis title default value is undefined. See
        # https://api.highcharts.com/highcharts/xAxis.title.text
        if (title := attrs.get("title")) and getattr(self, "supports_x_axis_title", False):
            config["title"] = title

        if (tick_interval := attrs.get("tick_interval")) is not None:
            config["tickIntervalMobile"] = tick_interval
            config["tickIntervalDesktop"] = tick_interval
        if (min_value := attrs.get("min")) is not None:
            config["min"] = min_value
        if (max_value := attrs.get("max")) is not None:
            config["max"] = max_value
        return config

    def get_y_axis_config(
        self,
        attrs: "StructValue",
    ) -> dict[str, Any]:
        config = {
            # TODO: hard code y_reversed for horizontal bar charts
            # "reversed": self.y_reversed,
        }

        # Only add y-axis title if supported
        if self.supports_y_axis_title:
            # Highcharts y-axis title default value is "Values". Set to undefined to
            # disable. See https://api.highcharts.com/highcharts/yAxis.title.text
            title = attrs["title"] or None
            config["title"] = title

        if (tick_interval := attrs.get("tick_interval")) is not None:
            config["tickIntervalMobile"] = tick_interval
            config["tickIntervalDesktop"] = tick_interval
        if (value_suffix := attrs.get("value_suffix")) is not None:
            config["labels"] = {
                "format": "{value} " + value_suffix,
            }
        if (min_value := attrs.get("min")) is not None:
            config["min"] = min_value
        if (max_value := attrs.get("max")) is not None:
            config["max"] = max_value
        return config

    def get_annotations_config(self, value: "StructValue") -> list[dict[str, Any]]:
        annotations_values: list[dict[str, Any]] = []
        for item in value.get("annotations", []):
            annotations_values.append(item.value.get_config())
        return annotations_values

    def get_series_data(
        self,
        value: "StructValue",
        headers: Sequence[str],
        rows: Sequence[list[str | int | float]],
    ) -> list[dict[str, Any]]:
        series = []

        for i, column in enumerate(headers[1:], start=1):
            # Extract data points, handling None/empty values
            data_points = [r[i] if r[i] != "" else None for r in rows]

            item = {
                "name": column,
                "data": data_points,
                "animation": False,
            }
            if self.supports_data_labels:
                item["dataLabels"] = value.get("show_data_labels")

            if getattr(self, "supports_markers", False):
                item["marker"] = value.get("show_markers")

            # Allow subclasses to specify additional parameters for each series
            for key, val in getattr(self, "extra_series_attributes", {}).items():
                item[key] = val

            if tooltip_suffix := value["y_axis"].get("tooltip_suffix"):
                item["tooltip"] = {
                    "valueSuffix": tooltip_suffix,
                }
            series.append(item)
        return series

    def get_additional_options(self, value: "StructValue") -> dict[str, Any]:
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

    def clean(self, value: "StructValue") -> "StructValue":
        result = super().clean(value)
        aspect_ratio_keys = [self.desktop_aspect_ratio, self.mobile_aspect_ratio]

        options_errors = {}
        if self.get_highcharts_chart_type(result) == "bar":
            for i, option in enumerate(result["options"]):
                if option.block_type in aspect_ratio_keys:
                    options_errors[i] = ValidationError("Bar charts do not support aspect ratio options.")

        if options_errors:
            raise blocks.StructBlockValidationError(
                block_errors={"options": blocks.StreamBlockValidationError(block_errors=options_errors)}
            )
        return result

    @cached_property
    def media(self) -> Media:
        return Media(
            js=[
                "https://code.highcharts.com/highcharts.js",
                "https://code.highcharts.com/modules/data.js",
                "https://code.highcharts.com/modules/exporting.js",
                "https://code.highcharts.com/modules/export-data.js",
                "https://code.highcharts.com/modules/accessibility.js",
                "https://code.highcharts.com/modules/annotations.js",
            ]
        )
