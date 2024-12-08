from django.db import models
from django.utils.translation import gettext_lazy as _


class BundleStatus(models.TextChoices):
    """The bundle statuses."""

    PENDING = "PENDING", _("Pending")
    IN_REVIEW = "IN_REVIEW", _("In Review")
    APPROVED = "APPROVED", _("Approved")
    RELEASED = "RELEASED", _("Released")


ACTIVE_BUNDLE_STATUSES = [BundleStatus.PENDING, BundleStatus.IN_REVIEW, BundleStatus.APPROVED]
ACTIVE_BUNDLE_STATUS_CHOICES = [
    (BundleStatus[choice].value, BundleStatus[choice].label) for choice in ACTIVE_BUNDLE_STATUSES
]
EDITABLE_BUNDLE_STATUSES = [BundleStatus.PENDING, BundleStatus.IN_REVIEW]
