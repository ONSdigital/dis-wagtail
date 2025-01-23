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
    PRIMARY = "primary", _("Primary")
    ALTERNATE = "alternate", _("Alternate")


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
