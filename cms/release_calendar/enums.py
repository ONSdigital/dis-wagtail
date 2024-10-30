from django.db import models
from django.utils.translation import gettext_lazy as _


class ReleaseStatus(models.TextChoices):
    """The release calendar page statuses.
    Note that both Provisional and Confirmed fall under "Upcoming" on the Release Calendar listing.
    """

    PROVISIONAL = "PROVISIONAL", _("Provisional")
    CONFIRMED = "CONFIRMED", _("Confirmed")
    CANCELLED = "CANCELLED", _("Cancelled")
    PUBLISHED = "PUBLISHED", _("Published")
