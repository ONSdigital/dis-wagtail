import logging
from typing import Any

from django.db.models.signals import pre_save
from django.dispatch import receiver

from cms.bundles.models import Bundle

from . import get_notifier

logger = logging.getLogger("cms.users")

notifier = get_notifier()


@receiver(pre_save, sender=Bundle)
def handle_bundle_in_review(sender, instance: Bundle, **kwargs: Any) -> None:
    """Handle when a bundle is set to In Review."""
    print("Bundle status changed to 'in review'")
