import logging
from datetime import timedelta
from typing import Any

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from cms.post_publish_actions.models import PostPublishAction, PostPublishActionQuerySet, PostPublishActionStatus

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Retry post-publish actions which have failed or timed out"

    def _get_actions_to_retry(self) -> PostPublishActionQuerySet:
        """Find the actions to be retried.
        An action should be retried if:
            - It was enqueued 2x the timeout ago.
            - It is marked as currently running (because of the above, it probably isn't).
            - It is marked as failed.
        """
        return (
            PostPublishAction.objects.unfinished()
            .active()
            .filter(
                enqueued_at__lte=timezone.now() - timedelta(seconds=settings.BUNDLE_POST_PUBLISH_TIMEOUT_SECONDS * 2),
                status__in=[PostPublishActionStatus.RUNNING, PostPublishActionStatus.FAILED],
            )
        )

    def handle(self, *args: Any, **options: Any) -> None:
        actions_to_retry = self._get_actions_to_retry()

        actions_to_retry_ids: set[int] = set(actions_to_retry.values_list("pk", flat=True))

        start_time = timezone.now()

        with transaction.atomic(durable=True):
            for action in actions_to_retry:
                # NB: These are enqueued on commit
                action.enqueue()

            # Update after enqueue so the iteration works
            actions_to_retry.update(
                status=PostPublishActionStatus.READY,
                enqueued_at=start_time,
                failed_reason="",
                duration=None,
                finished_at=None,
                timed_out_at=None,
            )

        while (
            actions_to_retry_ids
            and (timezone.now() - start_time).total_seconds() <= settings.BUNDLE_POST_PUBLISH_TIMEOUT_SECONDS
        ):
            actions_to_retry_ids -= set(
                PostPublishAction.objects.finished()
                .active()
                .filter(id__in=actions_to_retry_ids)
                .values_list("id", flat=True)
            )

        if actions_to_retry_ids:
            PostPublishAction.objects.active().unfinished().filter(id__in=actions_to_retry_ids).mark_timed_out()
            logger.error(
                "Post publish actions timeout",
                extra={
                    "outstanding_action_ids": actions_to_retry_ids,
                },
            )
