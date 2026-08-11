import logging
import time
from datetime import timedelta
from typing import TYPE_CHECKING, Any

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import F
from django.utils import timezone

from cms.core.db_router import force_write_db
from cms.post_publish_actions.models import PostPublishAction, PostPublishActionQuerySet, PostPublishActionStatus

if TYPE_CHECKING:
    from django.core.management.base import CommandParser

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Retry post-publish actions which have failed or timed out"

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "--dry-run",
            action="store_true",
            dest="dry_run",
            default=False,
            help="Dry run -- don't change anything.",
        )

    def _get_failed_actions(self) -> PostPublishActionQuerySet:
        return PostPublishAction.objects.active().filter(
            enqueued_at__lte=timezone.now() - timedelta(seconds=settings.BUNDLE_POST_PUBLISH_TIMEOUT_SECONDS * 2),
            status__in=[PostPublishActionStatus.RUNNING, PostPublishActionStatus.FAILED, PostPublishActionStatus.READY],
        )

    def _get_actions_to_retry(self) -> PostPublishActionQuerySet:
        """Find the actions to be retried.
        An action should be retried if:
            - It was enqueued 2x the timeout ago.
            - It is marked as currently running (because of the above, it probably isn't).
            - It hasn't run yet (also unlikely).
            - It is marked as failed.
        """
        return self._get_failed_actions().filter(
            retry_count__lt=settings.BUNDLE_POST_PUBLISH_MAX_RETRIES,
        )

    def _get_exhausted_actions(self) -> PostPublishActionQuerySet:
        """Find the actions which have exhausted their retries."""
        return self._get_failed_actions().filter(
            retry_count__gte=settings.BUNDLE_POST_PUBLISH_MAX_RETRIES,
        )

    @force_write_db()
    def handle(self, *args: Any, **options: Any) -> None:
        dry_run: bool = options.get("dry_run", False)
        if dry_run:
            logger.info("Running in dry-run mode. No changes will be made.")
        if exhausted_action_ids := list(self._get_exhausted_actions().values_list("pk", flat=True)):
            logger.error(
                "Post-publish actions have exhausted their retries",
                extra={
                    "event": "post_publish_action_retries_exhausted",
                    "exhausted_action_ids": exhausted_action_ids,
                    "max_retries": settings.BUNDLE_POST_PUBLISH_MAX_RETRIES,
                },
            )
        actions_to_retry = self._get_actions_to_retry()

        if not actions_to_retry.exists():
            logger.info("No post-publish actions to retry.")
            return

        actions_to_retry_ids: set[int] = set(actions_to_retry.values_list("pk", flat=True))

        start_time = timezone.now()

        if dry_run:
            logger.info(
                "Dry run mode: would retry the following post-publish actions",
                extra={"action_ids": list(actions_to_retry_ids)},
            )
            return

        with transaction.atomic(durable=True):
            for action in actions_to_retry:
                # NB: These are enqueued on commit
                action.enqueue()

            # Update after enqueue so the iteration works
            actions_to_retry.update(
                status=PostPublishActionStatus.READY,
                failed_reason="",
                duration=None,
                finished_at=None,
                timed_out_at=None,
                retry_count=F("retry_count") + 1,
            )

        while (
            actions_to_retry_ids
            and (timezone.now() - start_time).total_seconds() <= settings.BUNDLE_POST_PUBLISH_TIMEOUT_SECONDS
        ):
            actions_to_retry_ids -= set(
                PostPublishAction.objects.completed().filter(id__in=actions_to_retry_ids).values_list("id", flat=True)
            )

            # Only wait if there are bundles to check
            if actions_to_retry_ids:
                time.sleep(settings.BUNDLE_POST_PUBLISH_POLL_FREQUENCY)

        if actions_to_retry_ids:
            PostPublishAction.objects.pending().filter(id__in=actions_to_retry_ids).mark_timed_out()
            logger.error(
                "Post-publish actions timeout",
                extra={
                    "outstanding_action_ids": list(actions_to_retry_ids),
                },
            )
