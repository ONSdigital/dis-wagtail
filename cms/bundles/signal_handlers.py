import logging
from typing import Any

from django.conf import settings
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from cms.bundles.api import BundleAPIClient, BundleAPIClientError
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


def _build_bundle_data_for_api(bundle: Bundle) -> dict[str, Any]:
    """Build bundle data for API calls."""
    content = []

    # Add bundled pages
    for bundle_page in bundle.bundled_pages.all():
        if bundle_page.page:
            content.append({"id": str(bundle_page.page.pk), "type": "page"})

    # Add bundled datasets
    for bundle_dataset in bundle.bundled_datasets.all():
        if bundle_dataset.dataset:
            content.append({"id": bundle_dataset.dataset.namespace, "type": "dataset"})

    return {"title": bundle.name, "content": content}


@receiver(post_save, sender=Bundle)
def handle_bundle_dataset_api_sync(instance: Bundle, created: bool, **kwargs: Any) -> None:
    """Handle synchronization with the Dataset API for bundle creation and status updates."""
    if not getattr(settings, "ONS_BUNDLE_API_ENABLED", False):
        return

    client = BundleAPIClient()
    update_fields = kwargs.get("update_fields")

    try:
        if created:
            # Create new bundle in the API
            bundle_data = _build_bundle_data_for_api(instance)
            response = client.create_bundle(bundle_data)

            # Save the API ID returned by the API
            if "id" in response:
                instance.dataset_api_id = response["id"]
                instance.save(update_fields=["dataset_api_id"])
                logger.info("Created bundle %s in Dataset API with ID: %s", instance.pk, instance.dataset_api_id)
            else:
                logger.warning("Bundle %s created in API but no ID returned", instance.pk)

        elif instance.dataset_api_id:
            # For updates, only sync if we're not in the middle of setting the dataset_api_id
            if update_fields is None or "dataset_api_id" not in update_fields:
                # This is likely a status update or other field change
                client.update_bundle_status(instance.dataset_api_id, instance.status)
                logger.info("Updated bundle %s status to %s in Dataset API", instance.pk, instance.status)

    except BundleAPIClientError as e:
        logger.error("Failed to sync bundle %s with Dataset API: %s", instance.pk, e)
        # Don't raise the exception to avoid breaking the admin interface
        # The bundle will still be saved locally


@receiver(post_save, sender=BundleDataset)
def handle_bundle_dataset_added(instance: BundleDataset, **kwargs: Any) -> None:
    """Handle when a dataset is added to a bundle."""
    if not getattr(settings, "ONS_BUNDLE_API_ENABLED", False):
        return

    if instance.parent.dataset_api_id:
        client = BundleAPIClient()

        try:
            bundle_data = _build_bundle_data_for_api(instance.parent)
            client.update_bundle(instance.parent.dataset_api_id, bundle_data)
            logger.info("Updated bundle %s datasets in Dataset API", instance.parent.pk)

        except BundleAPIClientError as e:
            logger.error("Failed to update bundle %s datasets in Dataset API: %s", instance.parent.pk, e)


@receiver(post_delete, sender=BundleDataset)
def handle_bundle_dataset_removed(instance: BundleDataset, **kwargs: Any) -> None:
    """Handle when a dataset is removed from a bundle."""
    if not getattr(settings, "ONS_BUNDLE_API_ENABLED", False):
        return

    if instance.parent.dataset_api_id:
        client = BundleAPIClient()

        try:
            bundle_data = _build_bundle_data_for_api(instance.parent)
            client.update_bundle(instance.parent.dataset_api_id, bundle_data)
            logger.info("Updated bundle %s datasets in Dataset API", instance.parent.pk)

        except BundleAPIClientError as e:
            logger.error("Failed to update bundle %s datasets in Dataset API: %s", instance.parent.pk, e)


@receiver(post_delete, sender=Bundle)
def handle_bundle_deletion(instance: Bundle, **kwargs: Any) -> None:
    """Handle when a bundle is deleted."""
    if not getattr(settings, "ONS_BUNDLE_API_ENABLED", False):
        return

    if instance.dataset_api_id:
        client = BundleAPIClient()

        try:
            client.delete_bundle(instance.dataset_api_id)
            logger.info("Deleted bundle %s from Dataset API", instance.pk)

        except BundleAPIClientError as e:
            logger.error("Failed to delete bundle %s from Dataset API: %s", instance.pk, e)
            # Don't raise the exception to avoid breaking the deletion process
