import logging
import sched
import time
from datetime import timedelta
from typing import TYPE_CHECKING, Any

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from cms.bundles.enums import BundleStatus
from cms.bundles.models import Bundle
from cms.bundles.notifications.slack import notify_slack_of_bundle_pre_publish
from cms.bundles.utils import publish_bundle
from cms.core.db_router import force_write_db

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from django.core.management.base import CommandParser


class Command(BaseCommand):
    """The management command class for bundled publishing."""

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "--dry-run",
            action="store_true",
            dest="dry_run",
            default=False,
            help="Dry run -- don't change anything.",
        )
        parser.add_argument(
            "--include-future",
            type=int,
            default=None,
            help=(
                "Number of seconds in the future to include for publishing. "
                "Bundles in the future will be held until their publishing time."
            ),
        )

    def _handle_bundle_action(self, bundle: Bundle) -> None:
        try:
            # Refresh the bundle immediately before publishing, in case it's changed.
            bundle.refresh_from_db()

            # Confirm the bundle is still approved
            if bundle.status != BundleStatus.APPROVED:
                logger.error("Bundle no longer approved", extra={"bundle_id": bundle.pk})
                return

            with transaction.atomic():
                publish_bundle(bundle)
        except Exception:  # pylint: disable=broad-exception-caught
            logger.exception("Publish failed", extra={"bundle_id": bundle.pk, "event": "publish_failed"})

    @force_write_db()
    def handle(self, *args: Any, **options: Any) -> None:
        dry_run = False
        if options["dry_run"]:
            self.stdout.write("Will do a dry run.")
            dry_run = True

        max_release_date = timezone.now()
        if include_future := options["include_future"]:
            max_release_date += timedelta(seconds=include_future)

        bundles_to_publish = Bundle.objects.filter(
            status=BundleStatus.APPROVED, release_date__lte=max_release_date
        ).annotate_release_date()

        if not bundles_to_publish:
            self.stdout.write("No bundles to go live.")
        elif dry_run:
            self.stdout.write("\n---------------------------------")
            if bundles_to_publish:
                self.stdout.write("Bundles to be published:")
                for bundle in bundles_to_publish:
                    self.stdout.write(f"- {bundle.name} ({bundle.release_date.isoformat()})")
                    bundled_pages = [
                        f"{page.get_admin_display_title()} ({page.__class__.__name__})"
                        for page in bundle.get_bundled_pages().specific()
                    ]
                    self.stdout.write(f"  Pages: {'\n\t '.join(bundled_pages)}")
        else:
            # Explicitly use `time.time` so enterabs can be called with absolute timestamps.
            bundle_scheduler = sched.scheduler(timefunc=time.time)

            now_ts = bundle_scheduler.timefunc()

            self.stdout.write(f"Found {len(bundles_to_publish)} bundle(s) to publish")

            for bundle in bundles_to_publish:
                bundle_ts = bundle.release_date.timestamp()
                bundle_scheduler.enterabs(bundle_ts, 1, self._handle_bundle_action, argument=(bundle,))
                if bundle_ts > now_ts:
                    self.stdout.write(f"Publishing {bundle.name} in {bundle_ts - now_ts:.0f}s")
                    notify_slack_of_bundle_pre_publish(bundle, bundle.release_date)

            bundle_scheduler.run()
