from typing import ClassVar

from django.forms import widgets
from wagtail import blocks

from cms.datavis.blocks.base import BaseVisualisationBlock
from cms.datavis.blocks.utils import TextInputFloatBlock, TextInputIntegerBlock


class LineChartBlock(BaseVisualisationBlock):
    highcharts_chart_type = "line"
    supports_stacked_layout = False
    supports_x_axis_title = True
    supports_y_axis_title = True
    supports_data_labels = False
    supports_markers = True
    extra_series_attributes: ClassVar = {
        "connectNulls": True,
    }

    # Remove unsupported features
    select_chart_type = None
    use_stacked_layout = None
    show_data_labels = None

    class Meta:
        icon = "chart-line"


class BarColumnChartBlock(BaseVisualisationBlock):
    supports_stacked_layout = True
    supports_x_axis_title = False  # NB displayed as vertical axis for bar chart
    supports_y_axis_title = True
    supports_data_labels = True
    supports_markers = False

    # Remove unsupported features
    show_markers = None

    # Block overrides
    select_chart_type = blocks.ChoiceBlock(
        choices=[
            ("bar", "Bar"),
            ("column", "Column"),
        ],
        default="bar",
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

    class Meta:
        icon = "chart-bar"
