from enum import Enum

from django.db.models import TextChoices


class HighchartsTheme(TextChoices):
    PRIMARY = "primary", "Primary"
    ALTERNATE = "alternate", "Alternate"


class HighChartsChartType(Enum):
    LINE = "line"
    BAR = "bar"
    COLUMN = "column"
    SCATTER = "scatter"
    AREA = "area"


class AxisType(Enum):
    CATEGORICAL = "categorical"
    LINEAR = "linear"


class AxisChoices(TextChoices):
    X = "x", "X"
    Y = "y", "Y"


class BarColumnAxisChoices(TextChoices):
    """Variant for Bar/Column charts where the category label is always called X by Highcharts."""

    CATEGORY = "x", "Category axis"
    VALUE = "y", "Value axis"


class BarColumnChartTypeChoices(TextChoices):
    """Chart type choices for bar/column charts."""

    BAR = "bar", "Bar"
    COLUMN = "column", "Column"


class BarColumnConfidenceIntervalChartTypeChoices(TextChoices):
    """Chart type choices for bar/column charts with confidence intervals."""

    BAR = "columnrange", "Bar"
    COLUMN = "boxplot", "Column"


AXIS_TITLE_HELP_TEXT = "Only use axis titles if it is not clear from the title and subtitle what the axis represents."

# Block type names for chart blocks in SectionContentBlock
CHART_BLOCK_TYPES: frozenset[str] = frozenset(
    {
        "line_chart",
        "bar_column_chart",
        "bar_column_confidence_interval_chart",
        "scatter_plot",
        "area_chart",
    }
)
