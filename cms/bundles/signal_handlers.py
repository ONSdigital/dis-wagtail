from typing import Any

from django.db.models.signals import post_save
from django.dispatch import receiver

from cms.bundles.enums import BundleStatus
from cms.bundles.models import Bundle, BundleTeam
from cms.bundles.notifications.email import send_bundle_in_review_email, send_bundle_published_email


@receiver(post_save, sender=BundleTeam)
def handle_bundle_team_post_save(instance: BundleTeam, created: bool, **kwargs: Any) -> None:
    """Handle when a preview team is assigned to a bundle in review."""
    if created and instance.parent.status == BundleStatus.IN_REVIEW:
        send_bundle_in_review_email(bundle_team=instance)


@receiver(post_save, sender=Bundle)
def handle_bundle_in_preview(instance: Bundle, **kwargs: Any) -> None:
    """Handle when a bundle is set to In Preview."""
    if instance.status == BundleStatus.IN_REVIEW:
        active_unnotified_bundle_teams = [
            bundle_team
            for bundle_team in instance.teams.get_object_list()  # type: ignore[attr-defined]
            if bundle_team.team.is_active and not bundle_team.preview_notification_sent
        ]
        for bundle_team in active_unnotified_bundle_teams:
            send_bundle_in_review_email(bundle_team=bundle_team)


@receiver(post_save, sender=Bundle)
def handle_bundle_publication(instance: Bundle, **kwargs: Any) -> None:
    """Handle when a bundle is published."""
    if instance.status == BundleStatus.PUBLISHED:
        active_bundle_teams = [
            bundle_team
            for bundle_team in instance.teams.get_object_list()  # type: ignore[attr-defined]
            if bundle_team.team.is_active
        ]
        for bundle_team in active_bundle_teams:
            send_bundle_published_email(bundle_team=bundle_team)
