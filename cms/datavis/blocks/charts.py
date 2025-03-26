from typing import ClassVar

from cms.datavis.blocks.base import BaseVisualisationBlock


class LineChartBlock(BaseVisualisationBlock):
    highcharts_chart_type: ClassVar[str] = "line"
    supports_markers = True
    x_axis_type = "linear"

    # Remove the use_stacked_layout field from the block
    use_stacked_layout = None

    class Meta:
        icon = "chart-line"


class BarChartBlock(BaseVisualisationBlock):
    highcharts_chart_type: ClassVar[str] = "bar"

    class Meta:
        icon = "chart-bar"


# FIXME eventually combine bar/column charts into one type
class ColumnChartBlock(BaseVisualisationBlock):
    highcharts_chart_type: ClassVar[str] = "column"

    class Meta:
        icon = "chart-column"
