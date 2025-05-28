import json
from collections import defaultdict
from typing import TYPE_CHECKING, Any, ClassVar

from django.core.exceptions import ValidationError
from django.db.models import TextChoices
from django.forms import widgets
from wagtail import blocks

from cms.datavis.blocks.annotations import CoordinatePointAnnotationBlock
from cms.datavis.blocks.base import BaseVisualisationBlock
from cms.datavis.blocks.table import SimpleTableBlock, TableDataType
from cms.datavis.blocks.utils import TextInputFloatBlock, TextInputIntegerBlock
from cms.datavis.constants import AxisType, HighChartsChartType

if TYPE_CHECKING:
    from wagtail.blocks.struct_block import StructValue


class LineChartBlock(BaseVisualisationBlock):
    highcharts_chart_type = HighChartsChartType.LINE
    x_axis_type = AxisType.CATEGORY

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
    x_axis_type = AxisType.CATEGORY

    # Error codes
    ERROR_DUPLICATE_SERIES = "duplicate_series_number"
    ERROR_HORIZONTAL_BAR_NO_LINE = "horizontal_bar_no_line_overlay"
    ERROR_SERIES_OUT_OF_RANGE = "series_number_out_of_range"
    ERROR_ALL_SERIES_SELECTED = "all_series_selected"
    ERROR_BAR_CHART_NO_ASPECT_RATIO = "bar_chart_no_aspect_ratio"

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
                # Temporarily remove options. Title needs to be added back, so
                # there's no point removing this field entirely.
                "note",
                blocks.StaticBlock(
                    admin_text="(Temporary change) No options currently available for the category axis.",
                ),
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
            ("tick_interval_mobile", TextInputFloatBlock(label="Tick interval (mobile)", required=False)),
            ("tick_interval_desktop", TextInputFloatBlock(label="Tick interval (desktop)", required=False)),
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
        value = self.clean_series_customisation(value)
        value = self.clean_options(value)
        return value

    def clean_series_customisation(self, value: "StructValue") -> "StructValue":
        _, series = self.get_series_data(value)

        errors = {}
        stream_block_errors = {}
        seen_series_numbers = set()
        for i, block in enumerate(value.get("series_customisation", [])):
            if block.block_type == self.SERIES_AS_LINE_OVERLAY_BLOCK:
                if value.get("select_chart_type") == self.ChartTypeChoices.BAR:
                    stream_block_errors[i] = ValidationError(
                        "Horizontal bar charts do not support line overlays.", code=self.ERROR_HORIZONTAL_BAR_NO_LINE
                    )

                # Raise an error if the series number is not in the range of the number of series
                elif block.value < 1 or block.value > len(series):
                    stream_block_errors[i] = ValidationError(
                        "Series number out of range.", code=self.ERROR_SERIES_OUT_OF_RANGE
                    )

                elif block.value in seen_series_numbers:
                    stream_block_errors[i] = ValidationError(
                        "Duplicate series number.", code=self.ERROR_DUPLICATE_SERIES
                    )
                seen_series_numbers.add(block.value)

        if all(series_number in seen_series_numbers for series_number in range(1, len(series) + 1)):
            # Raise an error if all series are selected for line overlay. Ignore
            # the individual sub-block errors.
            errors["series_customisation"] = ValidationError(
                "There must be at least one column remaining. To draw lines only, use a Line Chart.",
                code=self.ERROR_ALL_SERIES_SELECTED,
            )
        elif stream_block_errors:
            errors["series_customisation"] = blocks.StreamBlockValidationError(block_errors=stream_block_errors)

        if errors:
            raise blocks.StructBlockValidationError(block_errors=errors)

        return value

    def clean_options(self, value: "StructValue") -> "StructValue":
        aspect_ratio_keys = [self.DESKTOP_ASPECT_RATIO, self.MOBILE_ASPECT_RATIO]

        errors = {}
        options_errors = {}
        if self.get_highcharts_chart_type(value) == self.ChartTypeChoices.BAR:
            for i, option in enumerate(value["options"]):
                if option.block_type in aspect_ratio_keys:
                    options_errors[i] = ValidationError(
                        "Bar charts do not support aspect ratio options.", code=self.ERROR_BAR_CHART_NO_ASPECT_RATIO
                    )

        if options_errors:
            errors["options"] = blocks.StreamBlockValidationError(block_errors=options_errors)

        if errors:
            raise blocks.StructBlockValidationError(block_errors=errors)

        return value


class ScatterPlotBlock(BaseVisualisationBlock):
    highcharts_chart_type = HighChartsChartType.SCATTER
    x_axis_type = AxisType.LINEAR

    # Remove unsupported features
    select_chart_type = None
    use_stacked_layout = None
    show_data_labels = None
    series_customisation = None
    show_markers = None

    TABLE_DEFAULT_DATA: TableDataType = (
        ["X", "Y", "Group"],
        ["", "", ""],
        ["", "", ""],
    )
    table = SimpleTableBlock(
        label="Data",
        help_text=(
            "Data is interpreted as three columns: x-value, y-value, group label. "
            "Column headings in row 1 are ignored. Other columns are ignored."
        ),
        default={"table_data": json.dumps({"data": TABLE_DEFAULT_DATA})},
    )

    annotations = blocks.StreamBlock(
        # Use coordinate-based annotations for scatter plots
        [
            ("point", CoordinatePointAnnotationBlock()),
        ],
        required=False,
    )

    class Meta:
        icon = "chart-line"

    def get_series_data(self, value: "StructValue") -> tuple[list[list[str | int | float]], list[dict[str, Any]]]:
        rows: list[list[str | int | float]] = value["table"].rows
        groups = defaultdict(list)

        for x, y, group_name, *_ in rows:
            groups[group_name].append((x, y))

        series = [
            {
                "name": group_name,
                "data": data_points,
                "marker": True,
            }
            for group_name, data_points in groups.items()
        ]
        return rows, series


class AreaChartBlock(BaseVisualisationBlock):
    highcharts_chart_type = HighChartsChartType.AREA
    x_axis_type = AxisType.CATEGORY

    # Error codes
    ERROR_EMPTY_CELLS = "empty_cells"

    # Remove unsupported features
    select_chart_type = None
    show_markers = None
    series_customisation = None
    show_data_labels = None
    use_stacked_layout = None

    class Meta:
        icon = "chart-area"

    def clean(self, value: "StructValue") -> "StructValue":
        value = super().clean(value)
        return self.clean_table_data(value)

    def clean_table_data(self, value: "StructValue") -> "StructValue":
        rows = value["table"].rows

        if any(cell == "" for row in rows[1:] for cell in row):
            raise blocks.StructBlockValidationError(
                {
                    "table": ValidationError(
                        "Empty cells in data. Area chart with missing values is not supported. "
                        "Enter data, or delete empty rows or columns.",
                        code=self.ERROR_EMPTY_CELLS,
                    )
                }
            )

        return value
