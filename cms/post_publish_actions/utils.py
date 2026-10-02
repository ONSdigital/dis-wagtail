import logging
import time
from collections.abc import Generator
from datetime import datetime
from typing import TYPE_CHECKING

from django.conf import settings
from django.db.models import Max
from django.db.models.expressions import Case, When
from django.utils import timezone
from wagtail.models import Page

from cms.bundles.notifications.slack import (
    notify_slack_of_post_publish_action_failure,
    notify_slack_of_post_publish_end,
)
from cms.core.db_router import force_write_db
from cms.core.utils import GeneratorCollector, release_db_connections

from .executor import wait_for_bundle_notifications
from .models import PostPublishAction, PostPublishActionStatus
from .registry import get_post_publish_actions

if TYPE_CHECKING:
    from cms.bundles.models import Bundle


logger = logging.getLogger(__name__)


def as_completed_actions_by_bundle(
    bundles: list[Bundle], start_time: datetime
) -> Generator[Bundle, None, list[Bundle]]:
    """Yield bundles as they finish, and return a list of timed-out bundles."""
    if not bundles:
        return []

    # Copy bundles to allow mutation
    bundles_to_check = list(bundles)

    while (
        bundles_to_check
        and (timezone.now() - start_time).total_seconds() <= settings.BUNDLE_POST_PUBLISH_TIMEOUT_SECONDS
    ):
        with force_write_db():
            unfinished_bundles: set[int] = set(
                PostPublishAction.objects.pending()
                .filter(bundle__in=bundles_to_check)
                .values_list("bundle_id", flat=True)
                .distinct()
            )

        for bundle in bundles_to_check.copy():
            if bundle.pk not in unfinished_bundles:
                yield bundle
                bundles_to_check.remove(bundle)

        # Only wait if there are bundles to check
        if bundles_to_check:
            release_db_connections()
            time.sleep(settings.BUNDLE_POST_PUBLISH_POLL_FREQUENCY)

    # Any remaining bundles will have timed out.
    return bundles_to_check


@force_write_db()
def post_publish_notify_slack(start_time: datetime, bundle: Bundle, *, publish_failed: bool = False) -> None:
    """Notifies slack when all post-publish actions are completed.

    Successful actions send their own notifications, so this also replies with failures if any.
    """
    as_completed_collector = GeneratorCollector(as_completed_actions_by_bundle([bundle], start_time))

    # Consume the generator
    as_completed_collector.consume()

    # If the generator returned a value, it means the bundle timed out
    if as_completed_collector.value:
        outstanding_actions = PostPublishAction.objects.pending().filter(bundle=bundle).mark_timed_out()
        logger.error(
            "Post-publish actions timeout",
            extra={
                "unfinished_bundles": [bundle.pk],
                "outstanding_actions": outstanding_actions,
            },
        )

    action_type_priority = Case(
        *[When(action_type=action_type, then=index) for index, action_type in enumerate(get_post_publish_actions())]
    )
    unsuccessful_actions = (
        PostPublishAction.objects.active()
        .filter(bundle=bundle)
        .exclude(status=PostPublishActionStatus.SUCCESSFUL)
        .select_related("page")
        .order_by(action_type_priority, "page_id")
    )

    for action in unsuccessful_actions:
        notify_slack_of_post_publish_action_failure(bundle, action.page, action)

    # Get end time based off last finished post-publish action marked critical
    # try to fall back to last finished action, else now
    completed_actions = PostPublishAction.objects.completed().filter(bundle=bundle, finished_at__gte=start_time)
    end_time = (
        PostPublishAction.objects.completed()
        .critical()
        .filter(bundle=bundle, finished_at__gte=start_time)
        .aggregate(latest_finish=Max("finished_at"))["latest_finish"]
        or completed_actions.aggregate(latest_finish=Max("finished_at"))["latest_finish"]
        or timezone.now()
    )
    wait_for_bundle_notifications(bundle.pk)
    notify_slack_of_post_publish_end(bundle, start_time, end_time, publish_failed=publish_failed)


def run_post_publish_actions_for(page: Page, bundle: Bundle | None) -> None:
    # Actions are returned in ascending priority order.
    # Sync path (no bundle): runs strictly in priority order.
    # Bundle path: enqueued in priority order, but execution order is not guaranteed (thread pool).
    registry = get_post_publish_actions()

    # TODO: Handle pages not in bundle.
    # For now, run synchronously.
    if bundle is None:
        for handler in registry.values():
            handler(page, bundle)
        return

    for action_type in registry:
        action, _created = PostPublishAction.objects.update_or_create(
            page=page,
            bundle=bundle,
            action_type=action_type,
            defaults={
                "status": PostPublishActionStatus.READY,
                "finished_at": None,
                "retry_count": 0,
            },
        )

        action.enqueue()
