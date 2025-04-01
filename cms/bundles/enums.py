from django.db import models


class BundleStatus(models.TextChoices):
    """The bundle statuses."""

    PENDING = "PENDING", "Pending"
    IN_REVIEW = "IN_REVIEW", "In Review"
    APPROVED = "APPROVED", "Approved"
    RELEASED = "RELEASED", "Released"


ACTIVE_BUNDLE_STATUSES = [BundleStatus.PENDING, BundleStatus.IN_REVIEW, BundleStatus.APPROVED]
ACTIVE_BUNDLE_STATUS_CHOICES = [
    (BundleStatus[choice].value, BundleStatus[choice].label) for choice in ACTIVE_BUNDLE_STATUSES
]
EDITABLE_BUNDLE_STATUSES = [BundleStatus.PENDING, BundleStatus.IN_REVIEW]
