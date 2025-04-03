from collections.abc import Sequence
from typing import Any, ClassVar, Optional

from django.forms.widgets import Media, RadioSelect
from django.utils.functional import cached_property
from wagtail import blocks
from wagtail.blocks.struct_block import StructValue

from cms.datavis.blocks.table import SimpleTableBlock
from cms.datavis.blocks.utils import TextInputFloatBlock, TextInputIntegerBlock
from cms.datavis.constants import HighchartsTheme


class PointAnnotationBlock(blocks.StructBlock):
    label = blocks.CharBlock(required=True)
    x_position = TextInputIntegerBlock(label="x-position", required=True)
    y_position = TextInputFloatBlock(label="y-position", required=True)


class BaseVisualisationBlock(blocks.StructBlock):
    # Extra attributes for subclasses
    highcharts_chart_type: ClassVar[str]
    supports_stacked_layout: ClassVar[bool]
    supports_x_axis_title: ClassVar[bool]
    supports_y_axis_title: ClassVar[bool]
    supports_data_labels: ClassVar[bool]
    supports_markers: ClassVar[bool]
    extra_item_attributes: ClassVar[dict[str, Any]]

    # Editable fields
    title = blocks.CharBlock()
    subtitle = blocks.CharBlock()
    caption = blocks.CharBlock(required=False)

    table = SimpleTableBlock(label="Data table")

    theme = blocks.ChoiceBlock(
        choices=HighchartsTheme.choices,
        default=HighchartsTheme.PRIMARY,
        widget=RadioSelect,
    )
    show_legend = blocks.BooleanBlock(default=True, required=False)
    show_data_labels = blocks.BooleanBlock(
        default=False,
        required=False,
        help_text="For cluster charts with 3 or more series, the data labels will be hidden.",
    )
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

    class Meta:
        template = "templates/components/streamfield/datavis/base_highcharts_chart_block.html"

    def get_context(self, value: "StructValue", parent_context: Optional[dict[str, Any]] = None) -> dict[str, Any]:
        context: dict[str, Any] = super().get_context(value, parent_context)

        # Add template and visualisation context to support rendering
        context["config"] = self.get_component_config(value)
        context["annotations_values"] = self.get_annotations_config(value)
        context["highcharts_chart_type"] = self.highcharts_chart_type
        return context

    def get_component_config(self, value: "StructValue") -> dict[str, Any]:
        headers: list[str] = value["table"].headers
        rows: list[list[str | int | float]] = value["table"].rows

        return {
            "chart": {
                "type": self.highcharts_chart_type,  # TODO: remove this once we upgrade to the latest version of the DS
            },
            "legend": {
                "enabled": value.get("show_legend", True),
            },
            "xAxis": self.get_x_axis_config(value.get("x_axis"), rows),
            "yAxis": self.get_y_axis_config(value.get("y_axis")),
            "series": self.get_series_data(value, headers, rows),
        }

    def get_x_axis_config(
        self,
        attrs: "StructValue",
        rows: Sequence[list[str | int | float]],
    ) -> dict[str, Any]:
        config: dict[str, Any] = {
            "type": "linear",
            "categories": [r[0] for r in rows],
        }

        # Only add x-axis title if supported and provided, as the Highcharts
        # x-axis title default value is undefined. See
        # https://api.highcharts.com/highcharts/xAxis.title.text
        if (title := attrs.get("title")) and getattr(self, "supports_x_axis_title", False):
            config["title"] = {
                "text": title,
            }

        if (tick_interval := attrs.get("tick_interval")) is not None:
            config["tickInterval"] = tick_interval
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
        if getattr(self, "supports_y_axis_title", False):
            # Highcharts y-axis title default value is "Values". Set to undefined to
            # disable. See https://api.highcharts.com/highcharts/yAxis.title.text
            title = attrs["title"] or None
            config["title"] = {
                "text": title,
            }

        if (tick_interval := attrs.get("tick_interval")) is not None:
            config["tickInterval"] = tick_interval
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
            # TODO: handle different annotation types
            # match item.block_type:
            #   case "point":
            annotations_values.append(
                {
                    "text": item.value["label"],
                    "point": {
                        "x": item.value["x_position"],
                        "y": item.value["y_position"],
                    },
                }
            )
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
                item["dataLabels"] = {
                    "enabled": value.get("show_data_labels"),
                }

            if getattr(self, "supports_markers", False):
                item["marker"] = {"enabled": value.get("show_markers")}

            for key, val in getattr(self, "extra_item_attributes", {}).items():
                item[key] = val

            if tooltip_suffix := value["y_axis"].get("tooltip_suffix"):
                item["tooltip"] = {
                    "valueSuffix": tooltip_suffix,
                }
            if getattr(self, "supports_stacked_layout", False) and value["use_stacked_layout"]:
                item["stacking"] = "normal"

            series.append(item)
        return series

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
