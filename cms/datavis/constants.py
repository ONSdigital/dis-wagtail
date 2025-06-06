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
