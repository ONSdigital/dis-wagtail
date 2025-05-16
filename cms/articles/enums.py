from django.db import models


class SortingChoices(models.TextChoices):
    """The choices for sorting."""

    ALPHABETIC = "ALPHABETIC", "Alphabetic"
    AS_SHOWN = "AS_SHOWN", "As shown"
