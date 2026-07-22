import logging
import time
from collections.abc import Generator
from datetime import datetime
from typing import TYPE_CHECKING

from django.conf import settings
from django.utils import timezone
from wagtail.models import Page

from cms.bundles.notifications.slack import notify_slack_of_post_publish_end
from cms.core.db_router import force_write_db
from cms.core.utils import GeneratorCollector

from .models import PostPublishAction, PostPublishActionStatus
from .registry import get_post_publish_actions

if TYPE_CHECKING:
    from cms.bundles.models import Bundle


logger = logging.getLogger(__name__)


@force_write_db()
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
            PostPublishAction.objects.pending()
            .filter(bundle__in=bundles_to_check)
            .values_list("bundle_id", flat=True)
            .distinct()
        )

        for bundle in bundles_to_check.copy():
            if bundle.pk not in unfinished_bundles:
                logger.info("bundle %s: %s actions finished" % (bundle.pk, bundle.name))
                yield bundle
                bundles_to_check.remove(bundle)
            else:
                logger.info("bundle %s: %s actions not yet finished" % (bundle.pk, bundle.name))

        # Only wait if there are bundles to check
        if bundles_to_check:
            time.sleep(settings.BUNDLE_POST_PUBLISH_POLL_FREQUENCY)

    # Any remaining bundles will have timed out.
    return bundles_to_check


@force_write_db()
def post_publish_notify_slack(start_time: datetime, bundle: Bundle, *, publish_failed: bool = False) -> None:
    as_completed_collector = GeneratorCollector(as_completed_actions_by_bundle([bundle], start_time))

    # Consume the generator
    as_completed_collector.consume()

    # If the generator returned a value, it means the bundle timed out
    if as_completed_collector.value:
        outstanding_actions = PostPublishAction.objects.pending().filter(bundle=bundle).mark_timed_out()
        logger.error(
            "Post publish actions timeout",
            extra={
                "unfinished_bundles": [bundle.pk],
                "outstanding_actions": outstanding_actions,
            },
        )
        logger.info("bundle %s: %s finished at %s"% (bundle.pk, bundle.name, timezone.now().isoformat()))
    notify_slack_of_post_publish_end(bundle, start_time, timezone.now(), publish_failed=publish_failed)


def run_post_publish_actions_for(page: Page, bundle: Bundle | None) -> None:
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
            },
        )

        action.enqueue()
