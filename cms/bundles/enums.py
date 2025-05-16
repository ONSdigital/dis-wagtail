from django.db import models


class BundleStatus(models.TextChoices):
    """The bundle statuses."""

    DRAFT = "DRAFT", "Draft"
    IN_REVIEW = "IN_REVIEW", "In Preview"
    APPROVED = "APPROVED", "Ready to publish"
    PUBLISHED = "PUBLISHED", "Published"


ACTIVE_BUNDLE_STATUSES = [BundleStatus.DRAFT, BundleStatus.IN_REVIEW, BundleStatus.APPROVED]
ACTIVE_BUNDLE_STATUS_CHOICES = [
    (BundleStatus[choice].value, BundleStatus[choice].label)  # type: ignore[misc]
    for choice in ACTIVE_BUNDLE_STATUSES
]
EDITABLE_BUNDLE_STATUSES = [BundleStatus.DRAFT, BundleStatus.IN_REVIEW]
PREVIEWABLE_BUNDLE_STATUSES = [BundleStatus.IN_REVIEW, BundleStatus.APPROVED]
