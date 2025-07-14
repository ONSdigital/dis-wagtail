import logging
from typing import Any

from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from cms.bundles.api import BundleAPIClient, BundleAPIClientError, get_data_admin_action_url
from cms.bundles.decorators import ons_bundle_api_enabled
from cms.bundles.enums import BundleStatus
from cms.bundles.models import Bundle, BundleDataset, BundleTeam
from cms.bundles.notifications.email import send_bundle_in_review_email, send_bundle_published_email

logger = logging.getLogger(__name__)


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


@receiver(post_save, sender=Bundle)
@ons_bundle_api_enabled
def handle_bundle_dataset_api_sync(instance: Bundle, **kwargs: Any) -> None:
    """Handle synchronization with the Dataset API for bundle status updates."""
    client = BundleAPIClient()
    update_fields = kwargs.get("update_fields")

    try:
        if instance.bundle_api_id and (update_fields is None or "bundle_api_id" not in update_fields):
            # This is likely a status update or other field change
            client.update_bundle_state(instance.bundle_api_id, instance.status)
            logger.info("Updated bundle %s status to %s in Dataset API", instance.pk, instance.status)

    except BundleAPIClientError as e:
        logger.error("Failed to sync bundle %s with Dataset API: %s", instance.pk, e)
        # Don't raise the exception to avoid breaking the admin interface
        # The bundle will still be saved locally


@receiver(post_save, sender=BundleDataset)
@ons_bundle_api_enabled
def handle_bundle_dataset_added(instance: BundleDataset, created: bool, **kwargs: Any) -> None:
    """Handle when a dataset is added to a bundle."""
    if not created or not instance.parent.bundle_api_id:
        return

    client = BundleAPIClient()

    try:
        # Add the content item to the bundle
        content_item = {
            "content_type": "DATASET",
            "metadata": {
                "dataset_id": instance.dataset.namespace,
                "edition_id": instance.dataset.edition,
                "version_id": instance.dataset.version,
            },
            "links": {
                "edit": get_data_admin_action_url("edit", instance.dataset.namespace, instance.dataset.version),
                "preview": get_data_admin_action_url("preview", instance.dataset.namespace, instance.dataset.version),
            },
        }
        response = client.add_content_to_bundle(instance.parent.bundle_api_id, content_item)

        # Find the content_id from the response
        content_item = next(
            (
                item
                for item in response.get("contents", [])
                if item.get("metadata", {}).get("dataset_id") == instance.dataset.namespace
                and item.get("metadata", {}).get("edition_id") == instance.dataset.edition
                and item.get("metadata", {}).get("version_id") == instance.dataset.version
            ),
            {},
        )

        if content_item and (content_id := content_item.get("id")):
            instance.content_api_id = content_id
            instance.save(update_fields=["content_api_id"])
            logger.info("Added content %s to bundle %s in Dataset API", instance.dataset.namespace, instance.parent.pk)
        else:
            logger.error("Could not find content_id in response for bundle %s", instance.parent.pk)

    except BundleAPIClientError as e:
        logger.error("Failed to add content to bundle %s in Dataset API: %s", instance.parent.pk, e)


@receiver(post_delete, sender=BundleDataset)
@ons_bundle_api_enabled
def handle_bundle_dataset_removed(instance: BundleDataset, **kwargs: Any) -> None:
    """Handle when a dataset is removed from a bundle."""
    if not instance.parent.bundle_api_id or not instance.content_api_id:
        return

    client = BundleAPIClient()

    try:
        content_id = instance.content_api_id
        client.delete_content_from_bundle(instance.parent.bundle_api_id, content_id)
        logger.info("Deleted content %s from bundle %s in Dataset API", content_id, instance.parent.pk)
    except BundleAPIClientError as e:
        logger.error("Failed to delete content %s from bundle %s in Dataset API: %s", content_id, instance.parent.pk, e)


@receiver(post_delete, sender=Bundle)
@ons_bundle_api_enabled
def handle_bundle_deletion(instance: Bundle, **kwargs: Any) -> None:
    """Handle when a bundle is deleted."""
    if instance.bundle_api_id:
        client = BundleAPIClient()

        try:
            client.delete_bundle(instance.bundle_api_id)
            logger.info("Deleted bundle %s from Dataset API", instance.pk)

        except BundleAPIClientError as e:
            logger.error("Failed to delete bundle %s from Dataset API: %s", instance.pk, e)
            # Don't raise the exception to avoid breaking the deletion process
