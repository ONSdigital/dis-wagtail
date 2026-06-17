from django.db import models
from django.utils.translation import gettext_lazy as _


class RelatedContentType(models.TextChoices):
    """Related content types."""

    ARTICLE = "ARTICLE", _("Article")
    DATASET = "DATASET", _("Dataset")
    METHODOLOGY = "METHODOLOGY", _("Methodology")
    TIME_SERIES = "TIME_SERIES", _("Time series")
    TOPIC = "TOPIC", _("Topic")
    INFORMATION = "INFORMATION", _("Information")
    REPORT = "REPORT", _("Report")
    WEBPAGE = "WEBPAGE", _("Webpage")
