from django.db import models


class SortingChoices(models.TextChoices):
    """The choices for sorting."""

    ALPHABETIC = "ALPHABETIC", "Alphabetic"
    MANUAL = "MANUAL", "Manual"
