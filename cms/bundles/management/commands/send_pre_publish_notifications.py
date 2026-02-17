import logging
from datetime import timedelta
from typing import Any

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db.models import Q
from django.db.models.functions import Coalesce
from django.utils import timezone

from cms.bundles.enums import BundleStatus
from cms.bundles.models import Bundle
from cms.bundles.notifications.slack import notify_slack_of_bundle_failure, notify_slack_of_bundle_pre_publish
from cms.workflows.utils import is_page_ready_to_publish

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """Send pre-publish notifications for upcoming bundles."""

    help = "Send pre-publish notifications for bundles scheduled to publish within the threshold"

    def _validate_bundle_for_publishing(self, bundle: Bundle) -> tuple[bool, str]:
        """Validate that all pages in the bundle are ready to publish.

        Returns:
            Tuple of (is_valid, error_message)
        """
        pages = bundle.get_bundled_pages()

        # Only validate pages if the bundle has pages
        for page in pages:
            if not is_page_ready_to_publish(page):
                return False, f"Page '{page.get_admin_display_title()}' is not ready to publish"

        return True, ""

    def handle(self, *args: Any, **options: Any) -> None:
        threshold_minutes = settings.SLACK_PUBLISH_PREVIEW_MINUTES
        now = timezone.now()
        threshold = now + timedelta(minutes=threshold_minutes)

        # Find approved bundles scheduled to publish within the threshold
        # that haven't been notified yet
        bundles = (
            Bundle.objects.filter(
                status=BundleStatus.APPROVED,
            )
            .filter(Q(slack_notification_ts="") | Q(slack_notification_ts__isnull=True))
            .filter(Q(publication_date__isnull=False) | Q(release_calendar_page__isnull=False))
            .annotate(scheduled_date=Coalesce("publication_date", "release_calendar_page__release_date"))
            .filter(
                scheduled_date__lte=threshold,
                scheduled_date__gte=now,
            )
        )

        if not bundles:
            self.stdout.write("No bundles requiring pre-publish notifications.")
            return

        for bundle in bundles:
            # Use the annotated scheduled_date
            scheduled_date = bundle.scheduled_date

            # Validate bundle before sending pre-publish notification
            is_valid, error_message = self._validate_bundle_for_publishing(bundle)

            if not is_valid:
                # Send failure notification if validation fails
                notify_slack_of_bundle_failure(
                    bundle=bundle,
                    failure_type="pre_publish_failed",
                    exception_message=error_message,
                    alert_type="Warning",
                )
                self.stdout.write(self.style.WARNING(f"Bundle validation failed for '{bundle.name}': {error_message}"))
            else:
                # Send pre-publish notification if validation passes
                notify_slack_of_bundle_pre_publish(bundle, scheduled_date)
                self.stdout.write(f"Sent pre-publish notification for bundle: {bundle.name}")
