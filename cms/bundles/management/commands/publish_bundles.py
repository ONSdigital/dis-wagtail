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
from cms.post_publish_actions.executor import run_in_executor as run_in_post_publish_executor
from cms.post_publish_actions.models import PostPublishAction, PostPublishActionStatus

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
        parser.add_argument(
            "--poll-frequency",
            type=int,
            default=settings.BUNDLE_POST_PUBLISH_POLL_FREQUENCY,
            help=("Number of seconds between checks of post-publish actions (default: %(default)r)"),
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
            publish_bundle(bundle)
        except Exception:  # pylint: disable=broad-exception-caught
            logger.exception("Publish failed", extra={"bundle_id": bundle.pk, "event": "publish_failed"})

    def _await_bundle_post_publish_actions(self, bundles: list[Bundle], poll_frequency: int) -> None:
        # Copy bundles to allow mutation
        bundles_to_check = list(bundles)

        start_time = time.monotonic()

        bundle_complete_futures = []

        while bundles_to_check and (time.monotonic() - start_time) <= settings.BUNDLE_POST_PUBLISH_TIMEOUT_SECONDS:
            unfinished_bundles: set[int] = set(
                PostPublishAction.objects.unfinished()
                .active()
                .filter(bundle__in=bundles_to_check)
                .values_list("bundle_id", flat=True)
                .distinct()
            )

            for bundle in bundles_to_check.copy():
                if bundle.pk not in unfinished_bundles:
                    bundle_complete_futures.append(
                        run_in_post_publish_executor(self._handle_bundle_post_publish_complete, bundle=bundle)
                    )
                    bundles_to_check.remove(bundle)

            # Only wait if there are bundles to check
            if bundles_to_check:
                time.sleep(poll_frequency)

        if bundles_to_check:
            outstanding_actions = (
                PostPublishAction.objects.unfinished()
                .active()
                .filter(bundle__in=bundles_to_check)
                .update(
                    status=PostPublishActionStatus.FAILED,
                    failed_reason="Timeout",
                    duration=None,
                    finished_at=timezone.now(),
                )
            )
            logger.error(
                "Post publish actions timeout",
                extra={
                    "unfinished_bundles": [bundle.pk for bundle in bundles_to_check],
                    "outstanding_actions": outstanding_actions,
                },
            )

        remaining_time = max(settings.BUNDLE_POST_PUBLISH_TIMEOUT_SECONDS - (time.monotonic() - start_time), 1)

        concurrent.futures.wait(
            bundle_complete_futures,
            return_when=concurrent.futures.ALL_COMPLETED,
            timeout=remaining_time + poll_frequency,
        )

    @force_write_db()
    def _handle_bundle_post_publish_complete(self, bundle: Bundle) -> None:
        notify_slack_of_post_publish_end(bundle, self.bundle_start_times[bundle], timezone.now())

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

            self._await_bundle_post_publish_actions(bundles_to_publish.copy(), options["poll_frequency"])
