from django.db.models import TextChoices
from django.utils.translation import gettext_lazy as _


class AnnotationStyle(TextChoices):
    ABOVE_LINE = "above_line", _("Above line")
    BELOW_LINE = "below_line", _("Below line")


class BarChartType(TextChoices):
    BAR = "bar", _("Bar")
    STACKED_BAR = "stacked_bar", _("Stacked bar")
    COLUMN = "column", _("Column")
    STACKED_COLUMN = "stacked_column", _("Stacked column")


class HighchartsTheme(TextChoices):
    PRIMARY = "primary", _("Primary")
    ALTERNATE = "alternate", _("Alternate")


class LegendPosition(TextChoices):
    TOP = "top", _("Top")
    BOTTOM = "bottom", _("Bottom")


HIGHCHARTS_THEMES = {
    "primary": (
        "#206095",  # ocean blue
        "#27A0CC",  # sky blue
        "#003C57",  # night blue
        "#118C7B",  # green
        "#A8BD3A",  # spring green
        "#871A5B",  # plum purple
        "#F66068",  # pink
        "#746CB1",  # light purple
        "#22D0B6",  # turquoise
    ),
    "alternate": (
        "#206095",  # ocean-blue
        "#27A0CC",  # sky blue
        "#871A5B",  # plum purple
        "#A8BD3A",  # spring green
        "#F66068",  # pink
    ),
}
