from collections.abc import Sequence
from typing import Any, ClassVar, Optional

from django.forms.widgets import Media
from django.utils.functional import cached_property
from wagtail import blocks
from wagtail.blocks.struct_block import StructValue

from cms.datavis.blocks.table import SimpleTableBlock
from cms.datavis.blocks.utils import TextInputFloatBlock, TextInputIntegerBlock


class PointAnnotationBlock(blocks.StructBlock):
    label = blocks.CharBlock(required=True)
    x_position = TextInputIntegerBlock(label="x-position", required=True)
    y_position = TextInputFloatBlock(label="y-position", required=True)


class BaseVisualisationBlock(blocks.StructBlock):
    title = blocks.CharBlock()
    subtitle = blocks.CharBlock()
    table = SimpleTableBlock(label="Data table")

    highcharts_chart_type: ClassVar[str]

    # Attributes
    show_legend = blocks.BooleanBlock(default=True, required=False)
    show_value_labels = blocks.BooleanBlock(
        default=False,
        required=False,
        help_text="For cluster charts with 3 or more series, the data labels will be hidden.",
    )
    use_stacked_layout = blocks.BooleanBlock(default=False, required=False)
    show_markers = blocks.BooleanBlock(default=False, required=False)

    # X axis
    x_axis = blocks.StructBlock(
        [
            ("label", blocks.CharBlock(label="Label", required=False)),
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
            ("label", blocks.CharBlock(required=False)),
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
        return context

    def get_component_config(self, value: "StructValue") -> dict[str, Any]:
        headers: list[str] = value["table"].headers
        rows: list[list[str | int | float]] = value["table"].rows

        return {
            "chart": {
                "type": self.highcharts_chart_type,
            },
            "legend": {
                "enabled": value.get("show_legend", True),
            },
            "xAxis": self.get_x_axis_config(value.get("x_axis"), headers, rows),
            "yAxis": self.get_y_axis_config(value.get("y_axis"), headers, rows),
            "series": self.get_series_data(value, headers, rows),
        }

    def get_x_axis_config(
        self,
        x_value: "StructValue",
        headers: Sequence[str],
        rows: Sequence[list[str | int | float]],
    ) -> dict[str, Any]:
        config = {
            "type": "linear",
            "title": {
                "enabled": True,
                "text": x_value.get("label") or headers[0],
            },
            "reversed": x_value.get("reversed"),
            "categories": [r[0] for r in rows],
        }
        if (tick_interval := x_value.get("tick_interval")) is not None:
            config["tickInterval"] = tick_interval
        if (min_value := x_value.get("min")) is not None:
            config["min"] = min_value
        if (max_value := x_value.get("max")) is not None:
            config["max"] = max_value
        return config

    def get_y_axis_config(
        self,
        y_value: "StructValue",
        headers: Sequence[str],
        rows: Sequence[list[str | int | float]],  # pylint: disable=unused-argument
    ) -> dict[str, Any]:
        config = {
            # TODO: hard code y_reversed for horizontal bar charts
            # "reversed": self.y_reversed,
        }
        label = y_value.get("label") or headers[1]
        if label:
            config["title"] = {
                "enabled": True,
                "text": label,
            }
        if (tick_interval := y_value.get("tick_interval")) is not None:
            config["tickInterval"] = tick_interval
        if (value_suffix := y_value.get("value_suffix")) is not None:
            config["labels"] = {
                "format": "{value} " + value_suffix,
            }
        if (min_value := y_value.get("min")) is not None:
            config["min"] = min_value
        if (max_value := y_value.get("max")) is not None:
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
        self, value: "StructValue", headers: Sequence[str], rows: Sequence[list[str | int | float]]
    ) -> list[dict[str, Any]]:
        series = []
        for i, column in enumerate(headers[1:], start=1):
            item = {
                "connectNulls": True,
                "name": column,
                "data": [r[i] for r in rows],
                "animation": False,
                "dataLabels": {
                    "enabled": value["show_value_labels"],
                },
            }
            if getattr(self, "supports_markers", False):
                item["marker"] = {
                    "enabled": value["show_markers"],
                }
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
