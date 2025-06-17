import logging
import time
from typing import TYPE_CHECKING, Any, cast

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction
from django.urls import reverse
from django.utils import timezone
from wagtail.log_actions import log

from cms.bundles.enums import BundleStatus
from cms.bundles.models import Bundle
from cms.bundles.notifications import notify_slack_of_publication_start, notify_slack_of_publish_end
from cms.bundles.utils import (
    serialize_bundle_content_for_published_release_calendar_page,
    serialize_datasets_for_release_calendar_page,
)
from cms.core.fields import StreamField
from cms.release_calendar.enums import ReleaseStatus

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from django.core.management.base import CommandParser


class Command(BaseCommand):
    """The management command class for bundled publishing."""

    base_url: str = ""

    def add_arguments(self, parser: "CommandParser") -> None:
        parser.add_argument(
            "--dry-run",
            action="store_true",
            dest="dry_run",
            default=False,
            help="Dry run -- don't change anything.",
        )

    def _update_related_release_calendar_page(self, bundle: Bundle) -> None:
        """Updates the release calendar page related to the bundle with the pages in the bundle."""
        page = bundle.release_calendar_page
        if page:  # To satisfy mypy, ensure page is not None
            content = serialize_bundle_content_for_published_release_calendar_page(bundle)
            datasets = serialize_datasets_for_release_calendar_page(bundle)

            page.content = cast(StreamField, content)
            page.datasets = cast(StreamField, datasets)
            page.status = ReleaseStatus.PUBLISHED
            revision = page.save_revision(log_action=True)
            revision.publish()

    # TODO: revisit after discussion.
    @transaction.atomic
    def handle_bundle(self, bundle: Bundle) -> None:
        """Manages the bundle publication.

        - published related pages
        - updates the release calendar entry
        """
        # only provide a URL if we can generate a full one
        inspect_url = self.base_url + reverse("bundle:inspect", args=(bundle.pk,)) if self.base_url else None

        logger.info(
            "Publishing Bundle",
            extra={
                "bundle_id": bundle.id,
                "event": "publishing_bundle",
            },
        )
        start_time = time.time()
        notify_slack_of_publication_start(bundle, url=inspect_url)
        for page in bundle.get_bundled_pages().specific(defer=True).select_related("latest_revision"):
            if workflow_state := page.current_workflow_state:
                # finish the workflow
                workflow_state.current_task_state.approve()
            else:
                # just run publish
                page.latest_revision.publish(log_action="wagtail.publish.scheduled")

        # update the related release calendar and publish
        if bundle.release_calendar_page_id:
            self._update_related_release_calendar_page(bundle)

        bundle.status = BundleStatus.PUBLISHED
        bundle.save()
        publish_duration = time.time() - start_time
        logger.info(
            "Published bundle",
            extra={
                "bundle_id": bundle.id,
                "duration": round(publish_duration * 1000, 3),
                "event": "published_bundle",
            },
        )

        notify_slack_of_publish_end(bundle, publish_duration, url=inspect_url)

        log(action="wagtail.publish.scheduled", instance=bundle)

    def handle(self, *args: Any, **options: dict[str, Any]) -> None:
        dry_run = False
        if options["dry_run"]:
            self.stdout.write("Will do a dry run.")
            dry_run = True

        self.base_url = getattr(settings, "WAGTAILADMIN_BASE_URL", "")

        bundles_to_publish = Bundle.objects.filter(status=BundleStatus.APPROVED, release_date__lte=timezone.now())
        if dry_run:
            self.stdout.write("\n---------------------------------")
            if bundles_to_publish:
                self.stdout.write("Bundles to be published:")
                for bundle in bundles_to_publish:
                    self.stdout.write(f"- {bundle.name}")
                    bundled_pages = [
                        f"{page.get_admin_display_title()} ({page.__class__.__name__})"
                        for page in bundle.get_bundled_pages().specific()
                    ]
                    self.stdout.write(f"  Pages: {'\n\t '.join(bundled_pages)}")

            else:
                self.stdout.write("No bundles to go live.")
        else:
            for bundle in bundles_to_publish:
                try:
                    self.handle_bundle(bundle)
                except Exception:  # pylint: disable=broad-exception-caught
                    logger.exception("Publish failed", extra={"bundle_id": bundle.id, "event": "publish_failed"})
