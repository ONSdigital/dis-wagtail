import concurrent.futures
import logging
import sched
import time
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone

from cms.bundles.enums import BundleStatus
from cms.bundles.models import Bundle
from cms.bundles.notifications.slack import notify_slack_of_bundle_pre_publish, notify_slack_of_post_publish_end
from cms.bundles.utils import publish_bundle
from cms.core.db_router import force_write_db
from cms.core.utils import GeneratorCollector
from cms.post_publish_actions.executor import run_in_support_executor as run_in_post_publish_support_executor
from cms.post_publish_actions.models import PostPublishAction
from cms.post_publish_actions.utils import as_completed_actions_by_bundle

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

            self.bundle_start_times[bundle] = timezone.now()

            if publish_bundle(bundle):
                self.published_bundle_ids.add(bundle.pk)

        except Exception:  # pylint: disable=broad-exception-caught
            logger.exception("Publish failed", extra={"bundle_id": bundle.pk, "event": "publish_failed"})

    def _await_bundle_post_publish_actions(self, bundles: list[Bundle]) -> None:
        # If there are no start times, no bundles were published
        if not self.bundle_start_times:
            return
        start_time = min(self.bundle_start_times.values())
        as_completed_collector = GeneratorCollector(as_completed_actions_by_bundle(bundles, start_time))

        bundle_complete_futures = []

        for completed_bundle in as_completed_collector:
            bundle_complete_futures.append(
                run_in_post_publish_support_executor(self._handle_bundle_post_publish_complete, bundle=completed_bundle)
            )

        if as_completed_collector.value:
            outstanding_actions = (
                PostPublishAction.objects.pending().filter(bundle__in=as_completed_collector.value).mark_timed_out()
            )
            logger.error(
                "Post publish actions timeout",
                extra={
                    "unfinished_bundles": [bundle.pk for bundle in as_completed_collector.value],
                    "outstanding_actions": outstanding_actions,
                },
            )
            for bundle in as_completed_collector.value:
                bundle_complete_futures.append(
                    run_in_post_publish_support_executor(self._handle_bundle_post_publish_complete, bundle=bundle)
                )

        remaining_time = max(
            settings.BUNDLE_POST_PUBLISH_TIMEOUT_SECONDS - (timezone.now() - start_time).total_seconds(), 1
        )

        concurrent.futures.wait(
            bundle_complete_futures,
            return_when=concurrent.futures.ALL_COMPLETED,
            timeout=remaining_time + settings.BUNDLE_POST_PUBLISH_POLL_FREQUENCY,
        )

    @force_write_db()
    def _handle_bundle_post_publish_complete(self, bundle: Bundle) -> None:
        notify_slack_of_post_publish_end(
            bundle,
            self.bundle_start_times[bundle],
            timezone.now(),
            publish_failed=bundle.pk not in self.published_bundle_ids,
        )

    @force_write_db()
    def handle(self, *args: Any, **options: Any) -> None:
        dry_run = False
        if options["dry_run"]:
            self.stdout.write("Will do a dry run.")
            dry_run = True

        max_release_date = timezone.now()
        if include_future := options["include_future"]:
            max_release_date += timedelta(seconds=include_future)

        # Force evaluate bundles
        bundles_to_publish = list(
            Bundle.objects.filter(
                status=BundleStatus.APPROVED, release_date__lte=max_release_date
            ).annotate_release_date()
        )

        self.bundle_start_times: dict[Bundle, datetime] = {}  # pylint: disable=attribute-defined-outside-init
        self.published_bundle_ids: set[int] = set()  # pylint: disable=attribute-defined-outside-init

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

            self._await_bundle_post_publish_actions(list(self.bundle_start_times))
