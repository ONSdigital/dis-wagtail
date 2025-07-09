import logging
from typing import Any

from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from cms.bundles.api import DatasetAPIClient, DatasetAPIClientError
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
    client = DatasetAPIClient()

    try:
        if created:
            # Create new bundle in the API
            bundle_data = _build_bundle_data_for_api(instance)
            response = client.create_bundle(bundle_data)

            # Save the API ID returned by the API
            if "id" in response:
                instance.dataset_api_id = response["id"]
                instance.save(update_fields=["dataset_api_id"])
                logger.info(f"Created bundle {instance.pk} in Dataset API with ID: {instance.dataset_api_id}")
            else:
                logger.warning(f"Bundle {instance.pk} created in API but no ID returned")

        elif instance.dataset_api_id:
            # Check if status has changed
            original_bundle = Bundle.objects.get(pk=instance.pk)
            if hasattr(original_bundle, "_state") and original_bundle._state.fields_cache:
                original_status = original_bundle._state.fields_cache.get("status")
                if original_status and original_status != instance.status:
                    # Status has changed, update in API
                    client.update_bundle_status(instance.dataset_api_id, instance.status)
                    logger.info(f"Updated bundle {instance.pk} status to {instance.status} in Dataset API")

    except DatasetAPIClientError as e:
        logger.error(f"Failed to sync bundle {instance.pk} with Dataset API: {e!s}")
        # Don't raise the exception to avoid breaking the admin interface
        # The bundle will still be saved locally


@receiver(post_save, sender=BundleDataset)
def handle_bundle_dataset_added(instance: BundleDataset, created: bool, **kwargs: Any) -> None:
    """Handle when a dataset is added to a bundle."""
    if instance.parent.dataset_api_id:
        client = DatasetAPIClient()

        try:
            bundle_data = _build_bundle_data_for_api(instance.parent)
            client.update_bundle(instance.parent.dataset_api_id, bundle_data)
            logger.info(f"Updated bundle {instance.parent.pk} datasets in Dataset API")

        except DatasetAPIClientError as e:
            logger.error(f"Failed to update bundle {instance.parent.pk} datasets in Dataset API: {e!s}")


@receiver(post_delete, sender=BundleDataset)
def handle_bundle_dataset_removed(instance: BundleDataset, **kwargs: Any) -> None:
    """Handle when a dataset is removed from a bundle."""
    if instance.parent.dataset_api_id:
        client = DatasetAPIClient()

        try:
            bundle_data = _build_bundle_data_for_api(instance.parent)
            client.update_bundle(instance.parent.dataset_api_id, bundle_data)
            logger.info(f"Updated bundle {instance.parent.pk} datasets in Dataset API")

        except DatasetAPIClientError as e:
            logger.error(f"Failed to update bundle {instance.parent.pk} datasets in Dataset API: {e!s}")


@receiver(post_delete, sender=Bundle)
def handle_bundle_deletion(instance: Bundle, **kwargs: Any) -> None:
    """Handle when a bundle is deleted."""
    if instance.dataset_api_id:
        client = DatasetAPIClient()

        try:
            client.delete_bundle(instance.dataset_api_id)
            logger.info(f"Deleted bundle {instance.pk} from Dataset API")

        except DatasetAPIClientError as e:
            logger.error(f"Failed to delete bundle {instance.pk} from Dataset API: {e!s}")
            # Don't raise the exception to avoid breaking the deletion process
