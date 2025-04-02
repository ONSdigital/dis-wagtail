from typing import ClassVar

from cms.datavis.blocks.base import BaseVisualisationBlock


class LineChartBlock(BaseVisualisationBlock):
    highcharts_chart_type = "line"
    supports_stacked_layout = False
    supports_x_axis_title = True
    supports_y_axis_title = True
    supports_data_labels = False
    supports_markers = True
    extra_item_attributes: ClassVar = {
        "connectNulls": True,
    }

    # Remove unsupported features
    use_stacked_layout = None
    show_data_labels = None

    class Meta:
        icon = "chart-line"


class BarChartBlock(BaseVisualisationBlock):
    highcharts_chart_type = "bar"
    supports_stacked_layout = True
    supports_x_axis_title = False
    supports_y_axis_title = True
    supports_data_labels = True
    supports_markers = False

    class Meta:
        icon = "chart-bar"


# FIXME eventually combine bar/column charts into one type
class ColumnChartBlock(BaseVisualisationBlock):
    highcharts_chart_type = "column"
    supports_stacked_layout = True
    supports_x_axis_title = True
    supports_y_axis_title = True
    supports_data_labels = False
    supports_markers = False

    class Meta:
        icon = "chart-column"
