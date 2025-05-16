from django.db import models


class ReleaseStatus(models.TextChoices):
    """The release calendar page statuses.
    Note that both Provisional and Confirmed fall under "Upcoming" on the Release Calendar listing.
    """

    PROVISIONAL = "PROVISIONAL", "Provisional"
    CONFIRMED = "CONFIRMED", "Confirmed"
    CANCELLED = "CANCELLED", "Cancelled"
    PUBLISHED = "PUBLISHED", "Published"


NON_PROVISIONAL_STATUSES = [ReleaseStatus.CONFIRMED, ReleaseStatus.PUBLISHED, ReleaseStatus.CANCELLED]
NON_PROVISIONAL_STATUS_CHOICES = [
    (ReleaseStatus[choice].value, ReleaseStatus[choice].label)  # type: ignore[misc]
    for choice in NON_PROVISIONAL_STATUSES
]
