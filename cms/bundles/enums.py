from django.db import models


class BundleStatus(models.TextChoices):
    """The bundle statuses."""

    PENDING = "PENDING", "Draft"
    IN_REVIEW = "IN_REVIEW", "In Preview"
    APPROVED = "APPROVED", "Ready to publish"
    RELEASED = "RELEASED", "Published"


ACTIVE_BUNDLE_STATUSES = [BundleStatus.PENDING, BundleStatus.IN_REVIEW, BundleStatus.APPROVED]
ACTIVE_BUNDLE_STATUS_CHOICES = [
    (BundleStatus[choice].value, BundleStatus[choice].label) for choice in ACTIVE_BUNDLE_STATUSES
]
EDITABLE_BUNDLE_STATUSES = [BundleStatus.PENDING, BundleStatus.IN_REVIEW]
PREVIEWABLE_BUNDLE_STATUSES = [BundleStatus.IN_REVIEW, BundleStatus.APPROVED]
