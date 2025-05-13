from typing import TYPE_CHECKING, Any, ClassVar

from django.core.exceptions import ValidationError
from django.db.models import TextChoices
from django.forms import widgets
from wagtail import blocks

from cms.datavis.blocks.base import BaseVisualisationBlock
from cms.datavis.blocks.utils import TextInputFloatBlock, TextInputIntegerBlock

if TYPE_CHECKING:
    from wagtail.blocks.struct_block import StructValue


class LineChartBlock(BaseVisualisationBlock):
    highcharts_chart_type = "line"
    extra_series_attributes: ClassVar = {
        "connectNulls": True,
    }

    # Remove unsupported features
    select_chart_type = None
    use_stacked_layout = None
    show_data_labels = None
    series_customisation = None

    class Meta:
        icon = "chart-line"


class BarColumnChartBlock(BaseVisualisationBlock):
    # Remove unsupported features
    show_markers = None

    class ChartTypeChoices(TextChoices):
        BAR = "bar", "Bar"
        COLUMN = "column", "Column"

    # Block overrides
    select_chart_type = blocks.ChoiceBlock(
        choices=ChartTypeChoices.choices,
        default=ChartTypeChoices.BAR,
        label="Display as",
        widget=widgets.RadioSelect,
    )
    show_data_labels = blocks.BooleanBlock(
        default=False,
        required=False,
        help_text="Bar charts only. For cluster charts with 3 or more series, the data labels will be hidden.",
    )
    # NB X_axis is labelled "Category axis" for bar/column charts
    x_axis = blocks.StructBlock(
        [
            (
                "tick_interval",
                TextInputIntegerBlock(label="Tick interval", required=False),
            ),
        ],
        label="Category axis",
    )
    # NB Y_axis is labelled "Value axis" for bar/column charts
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
            # TODO: Add min/max once support is added to the Design System
            # ("min", TextInputFloatBlock(label="Minimum", required=False)),
            # ("max", TextInputFloatBlock(label="Maximum", required=False)),
            ("tick_interval", TextInputFloatBlock(required=False)),
        ],
        label="Value axis",
    )
    show_legend = blocks.BooleanBlock(
        default=True,
        required=False,
        help_text="Legend displays only when there is more than one data series.",
    )
    SERIES_AS_LINE_OVERLAY_BLOCK = "series_as_line_overlay"
    series_customisation = blocks.StreamBlock(
        [
            (
                SERIES_AS_LINE_OVERLAY_BLOCK,
                TextInputIntegerBlock(help_text="The number of the series to display as a line overlay."),
            ),
        ],
        required=False,
    )

    class Meta:
        icon = "chart-bar"

    def get_series_customisation(self, value: "StructValue", series_number: int) -> dict[str, Any]:
        for block in value.get("series_customisation", []):
            if block.block_type == self.SERIES_AS_LINE_OVERLAY_BLOCK and block.value == series_number:
                return {"type": "line"}
        return {}

    def clean(self, value: "StructValue") -> "StructValue":
        value = super().clean(value)

        _, series = self.get_series_data(value)
        sub_block_errors = {}

        seen_series_numbers = set()
        for i, block in enumerate(value.get("series_customisation", [])):
            if block.block_type == self.SERIES_AS_LINE_OVERLAY_BLOCK:
                if block.value in seen_series_numbers:
                    sub_block_errors[i] = ValidationError("Duplicate series number.")
                seen_series_numbers.add(block.value)

                if value.get("select_chart_type") == self.ChartTypeChoices.BAR:
                    sub_block_errors[i] = ValidationError("Horizontal bar charts do not support line overlays.")

                # Raise an error if the series number is not in the range of the number of series
                if block.value < 1 or block.value > len(series):
                    sub_block_errors[i] = ValidationError("Series number out of range.")

        # Raise an error if there is only one data series
        if len(series) == len(seen_series_numbers):
            raise blocks.StructBlockValidationError(
                block_errors={
                    "series_customisation": ValidationError(
                        "There must be at least one column remaining. To draw lines only, use a Line Chart."
                    )
                }
            )

        if sub_block_errors:
            raise blocks.StructBlockValidationError(
                block_errors={"series_customisation": blocks.StreamBlockValidationError(block_errors=sub_block_errors)}
            )

        return value
