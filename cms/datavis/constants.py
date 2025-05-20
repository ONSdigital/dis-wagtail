from enum import Enum

from django.db.models import TextChoices
from django.utils.translation import gettext_lazy as _


class AnnotationStyle(TextChoices):
    ABOVE_LINE = "above_line", _("Above line")
    BELOW_LINE = "below_line", _("Below line")


class MarkerStyle(TextChoices):
    __empty__ = _("No markers")
    CIRCLE = "circle", _("Circle")
    SQUARE = "square", _("Square")
    TRIANGLE = "triangle", _("Triangle")
    DIAMOND = "diamond", _("Diamond")


class HighchartsTheme(TextChoices):
    PRIMARY = "primary", "Primary"
    ALTERNATE = "alternate", "Alternate"


class HighChartsChartType(Enum):
    LINE = "line"
    BAR = "bar"
    COLUMN = "column"
    SCATTER = "scatter"


class XAxisType(Enum):
    CATEGORY = "category"
    LINEAR = "linear"
