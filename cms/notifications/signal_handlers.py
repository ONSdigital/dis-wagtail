from typing import Any

from django.conf import settings
from django.db.models.signals import pre_save
from django.dispatch import receiver

from cms.bundles.models import Bundle

from .notifiers import AWS_SES_Notifier, LogNotifier

notifier = AWS_SES_Notifier() if settings.EMAIL_BACKEND == "django_ses.SESBackend" else LogNotifier()


@receiver(pre_save, sender=Bundle)
def handle_bundle_in_review(sender, instance: Bundle, **kwargs: Any) -> None:
    """Handle when a bundle is set to In Review."""
    try:
        # Try to retrieve the existing bundle
        old_bundle = sender.objects.get(pk=instance.pk)
    except sender.DoesNotExist:
        # Bundle doesn't exist yet - skip for this example
        pass
    else:
        print(f"New Bundle teams: {instance.active_team_ids}")
        print(f"Old Bundle teams: {old_bundle.active_team_ids}")
