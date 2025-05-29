import logging
import time
import uuid
from typing import TYPE_CHECKING, Any

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction
from django.urls import reverse
from django.utils import timezone
from wagtail.log_actions import log

from cms.bundles.enums import BundleStatus
from cms.bundles.models import Bundle
from cms.bundles.notifications import notify_slack_of_publication_start, notify_slack_of_publish_end
from cms.release_calendar.enums import ReleaseStatus

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from django.core.management.base import CommandParser
    from wagtail.models import Page


def serialize_page(page: "Page") -> dict[str, Any]:
    """Serializes a page to a dictionary."""
    return {
        "id": uuid.uuid4(),
        "type": "item",
        "value": {"page": page.pk, "title": "", "description": "", "external_url": ""},
    }


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
        content = []
        article_pages = []
        methodology_pages = []
        for page in bundle.get_bundled_pages():
            match page.specific_class.__name__:
                case "StatisticalArticlePage":
                    article_pages.append(serialize_page(page))
                case "MethodologyPage":
                    methodology_pages.append(serialize_page(page))

        if article_pages:
            content.append({"type": "release_content", "value": {"title": "Publications", "links": article_pages}})

        if methodology_pages:
            content.append({"type": "release_content", "value": {"title": "Methodology", "links": methodology_pages}})

        datasets = [
            {"type": "dataset_lookup", "id": uuid.uuid4(), "value": dataset["dataset"]}
            for dataset in bundle.bundled_datasets.all().values("dataset")
        ]

        page = bundle.release_calendar_page
        page.content = content
        page.datasets = datasets
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
