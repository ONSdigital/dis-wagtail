import logging
import time
from collections.abc import Generator
from datetime import datetime

from django.conf import settings
from django.utils import timezone

from cms.bundles.models import Bundle
from cms.bundles.notifications.slack import notify_slack_of_post_publish_end
from cms.core.utils import GeneratorCollector

from .models import PostPublishAction

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
        unfinished_bundles: set[int] = set(
            PostPublishAction.objects.unfinished()
            .active()
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
            time.sleep(settings.BUNDLE_POST_PUBLISH_POLL_FREQUENCY)

    # Any remaining bundles will have timed out.
    return bundles_to_check


def post_publish_notify_slack(start_time: datetime, bundle: Bundle) -> None:
    as_completed_collector = GeneratorCollector(as_completed_actions_by_bundle([bundle], start_time))

    # Consume the generator
    as_completed_collector.consume()

    # If the generator returned a value, it means the bundle timed out
    if as_completed_collector.value:
        outstanding_actions = PostPublishAction.objects.active().unfinished().filter(bundle=bundle).mark_timed_out()
        logger.error(
            "Post publish actions timeout",
            extra={
                "unfinished_bundles": [bundle.pk],
                "outstanding_actions": outstanding_actions,
            },
        )

    notify_slack_of_post_publish_end(bundle, start_time, timezone.now())
