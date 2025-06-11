import json
from collections import defaultdict
from typing import TYPE_CHECKING, Any, ClassVar

from django.core.exceptions import ValidationError
from django.forms import widgets
from wagtail import blocks

from cms.datavis.blocks.annotations import (
    LineAnnotationBarColumnBlock,
    LineAnnotationCategoricalBlock,
    LineAnnotationLinearBlock,
    PointAnnotationCategoricalBlock,
    PointAnnotationLinearBlock,
    RangeAnnotationBarColumnBlock,
    RangeAnnotationCategoricalBlock,
    RangeAnnotationLinearBlock,
)
from cms.datavis.blocks.base import BaseVisualisationBlock
from cms.datavis.blocks.table import SimpleTableBlock, TableDataType
from cms.datavis.blocks.utils import TextInputFloatBlock, TextInputIntegerBlock
from cms.datavis.constants import (
    AxisType,
    BarColumnChartTypeChoices,
    BarColumnConfidenceIntervalChartTypeChoices,
    HighChartsChartType,
)

if TYPE_CHECKING:
    from wagtail.blocks.struct_block import StructValue


class LineChartBlock(BaseVisualisationBlock):
    highcharts_chart_type = HighChartsChartType.LINE
    x_axis_type = AxisType.CATEGORICAL

    extra_series_attributes: ClassVar = {
        "connectNulls": True,
    }

    # Remove unsupported features
    select_chart_type = None
    use_stacked_layout = None
    show_data_labels = None
    series_customisation = None

    annotations = blocks.StreamBlock(
        [
            ("point", PointAnnotationCategoricalBlock()),
            ("range", RangeAnnotationCategoricalBlock()),
            ("reference_line", LineAnnotationCategoricalBlock()),
        ],
        required=False,
    )

    class Meta:
        icon = "chart-line"


class BarColumnChartBlock(BaseVisualisationBlock):
    x_axis_type = AxisType.CATEGORICAL

    # Error codes
    ERROR_DUPLICATE_SERIES = "duplicate_series_number"
    ERROR_HORIZONTAL_BAR_NO_LINE = "horizontal_bar_no_line_overlay"
    ERROR_SERIES_OUT_OF_RANGE = "series_number_out_of_range"
    ERROR_ALL_SERIES_SELECTED = "all_series_selected"
    ERROR_BAR_CHART_NO_ASPECT_RATIO = "bar_chart_no_aspect_ratio"

    # Remove unsupported features
    show_markers = None

    annotations = blocks.StreamBlock(
        [
            ("point", PointAnnotationCategoricalBlock()),
            ("range", RangeAnnotationBarColumnBlock()),
            ("reference_line", LineAnnotationBarColumnBlock()),
        ],
        required=False,
    )

    # Block overrides
    select_chart_type = blocks.ChoiceBlock(
        choices=BarColumnChartTypeChoices.choices,
        default=BarColumnChartTypeChoices.BAR,
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
                if value.get("select_chart_type") == BarColumnChartTypeChoices.BAR:
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
        if self.get_highcharts_chart_type(value) == BarColumnChartTypeChoices.BAR:
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


class BarColumnConfidenceIntervalChartBlock(BaseVisualisationBlock):
    x_axis_type = AxisType.CATEGORICAL

    # Error codes
    ERROR_BAR_CHART_NO_ASPECT_RATIO = "bar_chart_no_aspect_ratio"
    ERROR_UNMATCHED_RANGE = "unmatched_range"
    ERROR_INSUFFICIENT_COLUMNS = "insufficient_columns"
    ERROR_NON_NUMERIC_VALUE = "non_numeric_value"

    # Table data settings
    INITIAL_COLUMN_HEADINGS: tuple[str, ...] = ("Category", "Value", "Range min", "Range max")
    REQUIRED_COLUMN_COUNT = len(INITIAL_COLUMN_HEADINGS)
    TABLE_DEFAULT_DATA: TableDataType = (
        list(INITIAL_COLUMN_HEADINGS),
        ["", "", "", ""],
        ["", "", "", ""],
    )

    # Remove unsupported features
    show_markers = None
    use_stacked_layout = None
    show_legend = None  # Legend is editable differently for confidence interval charts
    show_data_labels = None
    theme = None

    annotations = blocks.StreamBlock(
        [
            ("point", PointAnnotationCategoricalBlock()),
            ("range", RangeAnnotationBarColumnBlock()),
            ("reference_line", LineAnnotationBarColumnBlock()),
        ],
        required=False,
    )

    # Block overrides
    table = SimpleTableBlock(
        label="Data",
        help_text=(
            "Data is interpreted as four columns: Category, Value, Range min, Range max. "
            "Column headings in row 1 are ignored. Other columns are ignored."
        ),
        default={"table_data": json.dumps({"data": TABLE_DEFAULT_DATA})},
    )
    select_chart_type = blocks.ChoiceBlock(
        choices=BarColumnConfidenceIntervalChartTypeChoices.choices,
        default=BarColumnConfidenceIntervalChartTypeChoices.BAR,
        label="Display as",
        widget=widgets.RadioSelect,
    )
    # NB X_axis is labelled "Category axis" for bar/column charts
    x_axis = blocks.StructBlock(
        [
            (
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
            ("tick_interval_mobile", TextInputFloatBlock(label="Tick interval (mobile)", required=False)),
            ("tick_interval_desktop", TextInputFloatBlock(label="Tick interval (desktop)", required=False)),
        ],
        label="Value axis",
    )
    estimate_line_label = blocks.CharBlock(
        required=True,
        help_text="Label for the estimate line in the legend",
    )
    uncertainty_range_label = blocks.CharBlock(
        required=True,
        help_text="Label for the uncertainty range in the legend",
    )

    class Meta:
        icon = "chart-column"

    def get_component_config(self, value: "StructValue") -> dict[str, Any]:
        config = super().get_component_config(value)
        match value["select_chart_type"]:
            case BarColumnConfidenceIntervalChartTypeChoices.BAR:
                config["isChartInverted"] = True
            case BarColumnConfidenceIntervalChartTypeChoices.COLUMN:
                # A box plot in Highcharts is a single series; therefore we use
                # custom component parameters to set the legend labels.
                config["estimateLineLabel"] = value.get("estimate_line_label")
                config["uncertaintyRangeLabel"] = value.get("uncertainty_range_label")
            case _:
                raise ValueError(f"Unknown chart type: {value['select_chart_type']}")
        return config

    def get_series_data(
        self,
        value: "StructValue",
    ) -> tuple[list[list[str | int | float]], list[dict[str, Any]]]:
        match value["select_chart_type"]:
            case BarColumnConfidenceIntervalChartTypeChoices.BAR:
                series = self.get_series_data_bar(value)
            case BarColumnConfidenceIntervalChartTypeChoices.COLUMN:
                series = self.get_series_data_column(value)
            case _:
                raise ValueError(f"Unknown chart type: {value['select_chart_type']}")
        return value["table"].rows, series

    def get_series_data_bar(self, value: "StructValue") -> list[dict[str, Any]]:
        values: list[str | int | float] = []
        confidence_intervals: list[tuple[str | int | float, str | int | float]] = []

        for row in value["table"].rows:
            confidence_intervals.append((row[2], row[3]))
            values.append(row[1])

        return [
            {
                "name": value.get("uncertainty_range_label"),
                "data": confidence_intervals,
            },
            {
                "name": value.get("estimate_line_label"),
                "data": values,
                "marker": True,
                "type": "scatter",
            },
        ]

    def get_series_data_column(self, value: "StructValue") -> list[dict[str, Any]]:
        return [
            {
                # Box plots are in the format
                # [whisker min, box bottom, centre line, box top, whisker max].
                # We do not render the whiskers, so we set them to the same as the
                # box extents.
                "data": [(row[2], row[2], row[1], row[3], row[3]) for row in value["table"].rows],
            }
        ]

    def clean(self, value: "StructValue") -> "StructValue":
        value = super().clean(value)
        value = self.clean_options(value)
        value = self.clean_table(value)
        return value

    def clean_options(self, value: "StructValue") -> "StructValue":
        aspect_ratio_keys = [self.DESKTOP_ASPECT_RATIO, self.MOBILE_ASPECT_RATIO]

        errors = {}
        options_errors = {}
        if self.get_highcharts_chart_type(value) == BarColumnConfidenceIntervalChartTypeChoices.BAR:  # Bar chart
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

    def clean_table(self, value: "StructValue") -> "StructValue":
        errors = {}
        # Category, Value, Range min, Range max
        if len(value["table"].headers) < self.REQUIRED_COLUMN_COUNT:
            errors["table"] = ValidationError(
                f"Data table must have {self.REQUIRED_COLUMN_COUNT} columns: Category, Value, Range min, Range max",
                code=self.ERROR_INSUFFICIENT_COLUMNS,
            )

        else:  # Only perform row-level validation if we have the expected number of columns.
            # Validate that range values are either both present or both absent.
            for row in value["table"].rows:
                if any((isinstance(cell, str) and cell.strip()) for cell in row[1:4]):
                    errors["table"] = ValidationError(
                        f'Non-numeric values in category "{row[0]}"',
                        code=self.ERROR_NON_NUMERIC_VALUE,
                    )

                if (row[2] == "") != (row[3] == ""):
                    errors["table"] = ValidationError(
                        f'Unmatched range for category "{row[0]}". Enter both '
                        "lower and upper limits, or leave both blank.",
                        code=self.ERROR_UNMATCHED_RANGE,
                    )

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
            ("point", PointAnnotationLinearBlock()),
            ("range", RangeAnnotationLinearBlock()),
            ("reference_line", LineAnnotationLinearBlock()),
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
    x_axis_type = AxisType.CATEGORICAL

    # Error codes
    ERROR_EMPTY_CELLS = "empty_cells"

    # Remove unsupported features
    select_chart_type = None
    show_markers = None
    series_customisation = None
    show_data_labels = None
    use_stacked_layout = None

    annotations = blocks.StreamBlock(
        [
            ("point", PointAnnotationCategoricalBlock()),
            ("range", RangeAnnotationCategoricalBlock()),
            ("reference_line", LineAnnotationCategoricalBlock()),
        ],
        required=False,
    )

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
