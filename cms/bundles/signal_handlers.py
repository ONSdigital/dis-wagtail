from typing import Any

from django.db.models.signals import post_save
from django.dispatch import receiver

from cms.bundles.email_notifications import (
    send_bundle_published_email,
    send_bundle_status_changed_to_in_review_email,
    send_team_added_to_bundle_in_review_email,
)
from cms.bundles.enums import BundleStatus
from cms.bundles.models import Bundle, BundleTeam


@receiver(post_save, sender=BundleTeam)
def handle_bundle_team_post_save(instance: BundleTeam, created: bool, **kwargs: Any) -> None:
    """Handle when a preview team is assigned to a bundle."""
    if created and instance.parent.status == BundleStatus.IN_REVIEW:
        send_team_added_to_bundle_in_review_email(bundle_team=instance)


@receiver(post_save, sender=Bundle)
def handle_bundle_in_preview(instance: Bundle, **kwargs: Any) -> None:
    """Handle when a bundle is set to In Preview."""
    if instance.status == BundleStatus.IN_REVIEW and not instance.preview_notification_sent:
        for bundle_team in instance.teams.get_object_list():  # type: ignore[attr-defined]
            send_bundle_status_changed_to_in_review_email(bundle=bundle_team.parent)

        instance.preview_notification_sent = True
        instance.save()


@receiver(post_save, sender=Bundle)
def handle_bundle_publication(instance: Bundle, **kwargs: Any) -> None:
    """Handle when a bundle is published."""
    if instance.status == BundleStatus.PUBLISHED:
        for bundle_team in instance.teams.get_object_list():  # type: ignore[attr-defined]
            send_bundle_published_email(bundle_team=bundle_team)
