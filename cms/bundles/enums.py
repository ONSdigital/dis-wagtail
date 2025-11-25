from enum import StrEnum

from django.db import models


class BundleStatus(models.TextChoices):
    """The bundle statuses."""

    DRAFT = "DRAFT", "Draft"
    IN_REVIEW = "IN_REVIEW", "In Preview"
    APPROVED = "APPROVED", "Ready to publish"
    PUBLISHED = "PUBLISHED", "Published"


class BundleContentItemState(StrEnum):
    APPROVED = "APPROVED"
    PUBLISHED = "PUBLISHED"

    def __eq__(self, other: object) -> bool:
        if isinstance(other, str):
            return self.value.lower() == other.lower()
        return super().__eq__(other)


ACTIVE_BUNDLE_STATUSES = [BundleStatus.DRAFT, BundleStatus.IN_REVIEW, BundleStatus.APPROVED]
ACTIVE_BUNDLE_STATUS_CHOICES = [
    (BundleStatus[choice].value, BundleStatus[choice].label) for choice in ACTIVE_BUNDLE_STATUSES
]
EDITABLE_BUNDLE_STATUSES = [BundleStatus.DRAFT, BundleStatus.IN_REVIEW]
PREVIEWABLE_BUNDLE_STATUSES = [BundleStatus.IN_REVIEW, BundleStatus.APPROVED]
