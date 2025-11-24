import json
from collections import defaultdict
from typing import TYPE_CHECKING, Any, ClassVar, Optional
from urllib.parse import ParseResult, urlparse

from django.conf import settings
from django.core.exceptions import ValidationError
from django.forms import widgets
from wagtail import blocks

from cms.core.blocks.struct_blocks import RelativeOrAbsoluteURLBlock
from cms.core.url_utils import is_hostname_in_domain
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
from cms.datavis.blocks.base import BaseChartBlock, BaseVisualisationBlock
from cms.datavis.blocks.table import SimpleTableBlock, TableDataType
from cms.datavis.blocks.utils import TextInputFloatBlock, TextInputIntegerBlock
from cms.datavis.constants import (
    AXIS_TITLE_HELP_TEXT,
    AxisType,
    BarColumnChartTypeChoices,
    BarColumnConfidenceIntervalChartTypeChoices,
    HighChartsChartType,
)

if TYPE_CHECKING:
    from wagtail.blocks.struct_block import StructValue


class LineChartBlock(BaseChartBlock):
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

    x_axis = blocks.StructBlock(
        [
            ("title", blocks.CharBlock(required=False, help_text=AXIS_TITLE_HELP_TEXT)),
            ("tick_interval_mobile", TextInputFloatBlock(label="Tick interval (mobile)", required=False)),
            ("tick_interval_desktop", TextInputFloatBlock(label="Tick interval (desktop)", required=False)),
        ]
    )
    y_axis = blocks.StructBlock(
        [
            ("title", blocks.CharBlock(required=False, help_text=AXIS_TITLE_HELP_TEXT)),
            ("tick_interval_mobile", TextInputFloatBlock(label="Tick interval (mobile)", required=False)),
            ("tick_interval_desktop", TextInputFloatBlock(label="Tick interval (desktop)", required=False)),
            ("min", TextInputFloatBlock(label="Minimum", required=False)),
            ("start_on_tick", blocks.BooleanBlock(label="Start on tick", default=True, required=False)),
            ("max", TextInputFloatBlock(label="Maximum", required=False)),
            ("end_on_tick", blocks.BooleanBlock(label="End on tick", default=True, required=False)),
            (
                "custom_reference_line",
                TextInputFloatBlock(
                    required=False,
                    help_text="Display the thicker reference line at a value other than zero, for indexed data",
                ),
            ),
        ],
    )

    class Meta:
        icon = "chart-line"


class BarColumnChartBlock(BaseChartBlock):
    x_axis_type = AxisType.CATEGORICAL
    MAX_SERIES_COUNT_WITH_DATA_LABELS = 2
    MAX_DATA_POINTS_WITH_DATA_LABELS = 20
    MAX_SERIES_COUNT_WITH_CUSTOM_REFERENCE_LINE = 1

    # Error codes
    ERROR_DUPLICATE_SERIES = "duplicate_series_number"
    ERROR_HORIZONTAL_BAR_NO_LINE = "horizontal_bar_no_line_overlay"
    ERROR_SERIES_OUT_OF_RANGE = "series_number_out_of_range"
    ERROR_ALL_SERIES_SELECTED = "all_series_selected"
    ERROR_BAR_CHART_NO_ASPECT_RATIO = "bar_chart_no_aspect_ratio"
    ERROR_HORIZONTAL_BAR_NO_CATEGORY_TITLE = "horizontal_bar_no_category_title"
    ERROR_NON_STACKED_COLUMN_NO_LINE = "non_stacked_column_no_line_overlay"
    ERROR_HORIZONTAL_BAR_NO_CUSTOM_REFERENCE_LINE = "horizontal_bar_no_custom_reference_line"
    ERROR_MULTIPLE_SERIES_NO_REFERENCE_LINE = "multiple_series_no_reference_line"

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
        help_text="""
        Data labels are only allowed on non-stacked bar charts with one or two series,
        and where the number of data points does not exceed 20 in any series.
        Data labels will be hidden for all other cases.
        """,
    )
    use_stacked_layout = blocks.BooleanBlock(default=False, required=False)
    # NB X_axis is labelled "Category axis" for bar/column charts
    x_axis = blocks.StructBlock(
        [
            (
                "title",
                blocks.CharBlock(
                    required=False,
                    help_text=AXIS_TITLE_HELP_TEXT,
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
                    help_text=AXIS_TITLE_HELP_TEXT,
                ),
            ),
            ("tick_interval_mobile", TextInputFloatBlock(label="Tick interval (mobile)", required=False)),
            ("tick_interval_desktop", TextInputFloatBlock(label="Tick interval (desktop)", required=False)),
            ("min", TextInputFloatBlock(label="Minimum", required=False)),
            ("start_on_tick", blocks.BooleanBlock(label="Start on tick", default=True, required=False)),
            ("max", TextInputFloatBlock(label="Maximum", required=False)),
            ("end_on_tick", blocks.BooleanBlock(label="End on tick", default=True, required=False)),
            (
                "custom_reference_line",
                TextInputFloatBlock(
                    label="Custom reference line",
                    required=False,
                    help_text="Display the thicker reference line at a value other than zero, for indexed data. "
                    "Available on column charts only.",
                ),
            ),
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
        self.validate_series_customisation(value)
        self.validate_options(value)
        self.validate_x_axis(value)
        self.validate_y_axis(value)
        return value

    def validate_series_customisation(self, value: "StructValue") -> "StructValue":
        _, series = self.get_series_data(value)

        errors = {}
        stream_block_errors = {}
        seen_series_numbers = set()
        series_count_when_validating_line_overlay = 2
        for i, block in enumerate(value.get("series_customisation", [])):
            if block.block_type == self.SERIES_AS_LINE_OVERLAY_BLOCK:
                if value.get("select_chart_type") == BarColumnChartTypeChoices.BAR:
                    stream_block_errors[i] = ValidationError(
                        "Horizontal bar charts do not support line overlays.", code=self.ERROR_HORIZONTAL_BAR_NO_LINE
                    )

                elif (
                    value.get("select_chart_type") == BarColumnChartTypeChoices.COLUMN
                    and not value.get("use_stacked_layout")
                ) and len(series) > series_count_when_validating_line_overlay:
                    stream_block_errors[i] = ValidationError(
                        "To show a line overlay with multiple series, use a stacked layout",
                        code=self.ERROR_NON_STACKED_COLUMN_NO_LINE,
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

    def validate_x_axis(self, value: "StructValue") -> None:
        if value.get("select_chart_type") == BarColumnChartTypeChoices.BAR and value.get("x_axis").get("title"):
            raise blocks.StructBlockValidationError(
                {
                    "x_axis": blocks.StructBlockValidationError(
                        block_errors={
                            "title": ValidationError(
                                "Category axis title is not supported for horizontal bar charts.",
                                code=self.ERROR_HORIZONTAL_BAR_NO_CATEGORY_TITLE,
                            )
                        }
                    )
                }
            )

    def validate_y_axis(self, value: "StructValue") -> None:
        if value.get("y_axis").get("custom_reference_line"):
            if value.get("select_chart_type") == BarColumnChartTypeChoices.BAR:
                raise blocks.StructBlockValidationError(
                    block_errors={
                        "y_axis": blocks.StructBlockValidationError(
                            block_errors={
                                "custom_reference_line": ValidationError(
                                    "Custom reference line is not supported for bar charts.",
                                    code=self.ERROR_HORIZONTAL_BAR_NO_CUSTOM_REFERENCE_LINE,
                                )
                            }
                        )
                    }
                )

            if len(value["table"].headers) > self.MAX_SERIES_COUNT_WITH_CUSTOM_REFERENCE_LINE + 1:
                # NOTE Currently this prevents use of custom reference line even
                # when the second series is a line overlay.
                raise blocks.StructBlockValidationError(
                    {
                        "y_axis": blocks.StructBlockValidationError(
                            block_errors={
                                "custom_reference_line": ValidationError(
                                    "Custom reference line is supported for single-series data only.",
                                    code=self.ERROR_MULTIPLE_SERIES_NO_REFERENCE_LINE,
                                )
                            }
                        )
                    }
                )

    def validate_options(self, value: "StructValue") -> None:
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

    def get_series_item(
        self,
        value: "StructValue",
        series_number: int,
        series_name: str,
        rows: list[list[str | int | float]],
    ) -> dict[str, Any]:
        item = super().get_series_item(value, series_number, series_name, rows)

        # Add data labels configuration.
        # This is only supported for non-stacked horizontal bar charts with 1 or 2 series,
        # and where the number of data points does not exceed 20.
        if (
            value.get("show_data_labels")
            and value.get("select_chart_type") == BarColumnChartTypeChoices.BAR
            and not value.get("use_stacked_layout")
            # +1 to allow for the categories in the first column
            and len(value["table"].headers) <= self.MAX_SERIES_COUNT_WITH_DATA_LABELS + 1
            and len(value["table"].rows) <= self.MAX_DATA_POINTS_WITH_DATA_LABELS
        ):
            item["dataLabels"] = True

        return item


class BarColumnConfidenceIntervalChartBlock(BaseChartBlock):
    x_axis_type = AxisType.CATEGORICAL

    # Error codes
    ERROR_BAR_CHART_NO_ASPECT_RATIO = "bar_chart_no_aspect_ratio"
    ERROR_UNMATCHED_RANGE = "unmatched_range"
    ERROR_INSUFFICIENT_COLUMNS = "insufficient_columns"
    ERROR_NON_NUMERIC_VALUE = "non_numeric_value"
    ERROR_HORIZONTAL_BAR_NO_CATEGORY_TITLE = "horizontal_bar_no_category_title"

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
        [("title", blocks.CharBlock(required=False, help_text=AXIS_TITLE_HELP_TEXT))],
        label="Category axis",
    )
    # NB Y_axis is labelled "Value axis" for bar/column charts
    y_axis = blocks.StructBlock(
        [
            ("title", blocks.CharBlock(required=False, help_text=AXIS_TITLE_HELP_TEXT)),
            ("tick_interval_mobile", TextInputFloatBlock(label="Tick interval (mobile)", required=False)),
            ("tick_interval_desktop", TextInputFloatBlock(label="Tick interval (desktop)", required=False)),
            ("min", TextInputFloatBlock(label="Minimum", required=False)),
            ("start_on_tick", blocks.BooleanBlock(label="Start on tick", default=True, required=False)),
            ("max", TextInputFloatBlock(label="Maximum", required=False)),
            ("end_on_tick", blocks.BooleanBlock(label="End on tick", default=True, required=False)),
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
                "data": [
                    (row[2], row[2], row[1], row[3], row[3])
                    if row[2] and row[3]
                    else (row[1], row[1], row[1], row[1], row[1])
                    for row in value["table"].rows
                ],
            }
        ]

    def clean(self, value: "StructValue") -> "StructValue":
        value = super().clean(value)
        self.validate_options(value)
        self.validate_table(value)
        self.validate_x_axis(value)
        return value

    def validate_options(self, value: "StructValue") -> None:
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

    def validate_table(self, value: "StructValue") -> None:
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

    def validate_x_axis(self, value: "StructValue") -> None:
        if value.get("select_chart_type") == BarColumnConfidenceIntervalChartTypeChoices.BAR and value.get(
            "x_axis"
        ).get("title"):
            raise blocks.StructBlockValidationError(
                {
                    "x_axis": blocks.StructBlockValidationError(
                        block_errors={
                            "title": ValidationError(
                                "Category axis title is not supported for horizontal bar charts.",
                                code=self.ERROR_HORIZONTAL_BAR_NO_CATEGORY_TITLE,
                            )
                        }
                    )
                }
            )


class ScatterPlotBlock(BaseChartBlock):
    highcharts_chart_type = HighChartsChartType.SCATTER
    x_axis_type = AxisType.LINEAR

    # Remove unsupported features
    select_chart_type = None
    use_stacked_layout = None
    show_data_labels = None
    series_customisation = None
    show_markers = None

    x_axis = blocks.StructBlock(
        [
            ("title", blocks.CharBlock(required=False, help_text=AXIS_TITLE_HELP_TEXT)),
            ("tick_interval_mobile", TextInputFloatBlock(label="Tick interval (mobile)", required=False)),
            ("tick_interval_desktop", TextInputFloatBlock(label="Tick interval (desktop)", required=False)),
            ("min", TextInputFloatBlock(label="Minimum", required=False)),
            ("start_on_tick", blocks.BooleanBlock(label="Start on tick", default=False, required=False)),
            ("max", TextInputFloatBlock(label="Maximum", required=False)),
            ("end_on_tick", blocks.BooleanBlock(label="End on tick", default=False, required=False)),
        ]
    )
    y_axis = blocks.StructBlock(
        [
            ("title", blocks.CharBlock(required=False, help_text=AXIS_TITLE_HELP_TEXT)),
            ("tick_interval_mobile", TextInputFloatBlock(label="Tick interval (mobile)", required=False)),
            ("tick_interval_desktop", TextInputFloatBlock(label="Tick interval (desktop)", required=False)),
            ("min", TextInputFloatBlock(label="Minimum", required=False)),
            ("start_on_tick", blocks.BooleanBlock(label="Start on tick", default=True, required=False)),
            ("max", TextInputFloatBlock(label="Maximum", required=False)),
            ("end_on_tick", blocks.BooleanBlock(label="End on tick", default=True, required=False)),
        ]
    )

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


class AreaChartBlock(BaseChartBlock):
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

    x_axis = blocks.StructBlock(
        [
            ("title", blocks.CharBlock(required=False, help_text=AXIS_TITLE_HELP_TEXT)),
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
    y_axis = blocks.StructBlock(
        [
            ("title", blocks.CharBlock(required=False, help_text=AXIS_TITLE_HELP_TEXT)),
            ("tick_interval_mobile", TextInputFloatBlock(label="Tick interval (mobile)", required=False)),
            ("tick_interval_desktop", TextInputFloatBlock(label="Tick interval (desktop)", required=False)),
            ("min", TextInputFloatBlock(label="Minimum", required=False)),
            ("start_on_tick", blocks.BooleanBlock(label="Start on tick", default=True, required=False)),
            ("max", TextInputFloatBlock(label="Maximum", required=False)),
            ("end_on_tick", blocks.BooleanBlock(label="End on tick", default=True, required=False)),
        ]
    )

    class Meta:
        icon = "chart-area"

    def clean(self, value: "StructValue") -> "StructValue":
        value = super().clean(value)
        self.validate_table_data(value)
        return value

    def validate_table_data(self, value: "StructValue") -> None:
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


class IframeBlock(BaseVisualisationBlock):
    iframe_source_url = RelativeOrAbsoluteURLBlock(
        required=True,
        help_text=(
            "Enter the full URL or relative URL path (preferred) of the visualisation you want to embed. "
            "A full URL must start with <code>https://</code>, the hostname must match one of the allowed domains. "
            "The URL path must start with an allowed prefix for both full or relative URLs. "
            f"Allowed domains: "
            f"{' or '.join(f'<code>{d}</code>' for d in settings.IFRAME_VISUALISATION_ALLOWED_DOMAINS)}. "
            f"Allowed path prefixes: "
            f"{' or '.join(f'<code>{p}</code>' for p in settings.IFRAME_VISUALISATION_PATH_PREFIXES)}."
        ),
    )

    class Meta:
        icon = "code"

    def clean(self, value: "StructValue") -> "StructValue":
        errors = {}

        for field_name, field in self.child_blocks.items():
            if field.required and not value.get(field_name):
                errors[field_name] = ValidationError("This field is required.")

        errors |= self._validate_source_url(value)

        if errors:
            raise blocks.StructBlockValidationError(errors)

        return super().clean(value)

    def _validate_source_url(self, value: "StructValue") -> dict[str, ValidationError]:
        """Validate the source URL of the iframe. Validation errors are returned as an errors dict.
        The URL can be either absolute (with scheme and hostname) or relative (path only).
        """
        source_url = value["iframe_source_url"]
        if not source_url:
            return {"iframe_source_url": ValidationError("Please enter a valid URL.")}

        parsed_url = urlparse(source_url)

        if parsed_url.scheme or parsed_url.netloc:
            # If a scheme or netloc is present, validate as an absolute URL
            return self._validate_absolute_source_url(parsed_url, source_url=source_url)

        # Otherwise, validate as a relative URL path
        return self._validate_source_url_path(parsed_url)

    def _validate_absolute_source_url(self, parsed_url: ParseResult, *, source_url: str) -> dict[str, ValidationError]:
        """Validate the absolute source URL of the iframe. Validation errors are returned as an errors dict."""
        errors = {}
        allowed_domains = " or ".join(settings.IFRAME_VISUALISATION_ALLOWED_DOMAINS)

        # Check the original source_url string scheme here, as URL parse is permissive of malformed schemes
        if not (source_url.startswith("https://") and parsed_url.hostname):
            errors["iframe_source_url"] = ValidationError(
                "Please enter a valid URL. Full URLs must start with 'https://'."
            )
        elif not any(
            is_hostname_in_domain(parsed_url.hostname, allowed_domain)
            for allowed_domain in settings.IFRAME_VISUALISATION_ALLOWED_DOMAINS
        ):
            errors["iframe_source_url"] = ValidationError(
                f"The URL hostname is not in the list of allowed domains: {allowed_domains}."
            )
        else:
            path_errors = self._validate_source_url_path(parsed_url)
            errors.update(path_errors)

        return errors

    @staticmethod
    def _validate_source_url_path(parsed_url: ParseResult) -> dict[str, ValidationError]:
        """Validate the path of the iframe source URL. Validation errors are returned as an errors dict."""
        errors = {}
        url_path = parsed_url.path.rstrip("/")
        allowed_prefixes = [prefix.rstrip("/") for prefix in settings.IFRAME_VISUALISATION_PATH_PREFIXES]

        if not any(
            url_path.startswith(prefix + "/") and len(url_path) > len(prefix) + 1 for prefix in allowed_prefixes
        ):
            readable_prefixes = " or ".join(settings.IFRAME_VISUALISATION_PATH_PREFIXES)
            errors["iframe_source_url"] = ValidationError(
                f"The URL path is not allowed. It must start with: {readable_prefixes}, "
                "and include a subpath after the prefix."
            )
        return errors

    def get_component_config(self, value: "StructValue") -> dict[str, Any]:
        config = {
            "headingLevel": 3,
            "title": value.get("title"),
            "subtitle": value.get("subtitle"),
            "caption": value.get("caption"),
            "description": value.get("audio_description"),
            "iframeUrl": value.get("iframe_source_url"),
        }

        return config

    def get_context(self, value: "StructValue", parent_context: Optional[dict[str, Any]] = None) -> dict[str, Any]:
        context: dict[str, Any] = super().get_context(value, parent_context)

        context["chart_config"] = self.get_component_config(value)
        return context
