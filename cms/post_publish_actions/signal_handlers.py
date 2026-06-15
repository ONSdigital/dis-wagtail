from functools import partial
from typing import Any

from django.conf import settings
from django.db import transaction
from wagtail.models import Page, Revision
from wagtail.signals import page_published

from cms.bundles.utils import get_active_bundle_for_page

from .executor import run_action, run_in_executor
from .models import PostPublishAction, PostPublishActionStatus
from .registry import get_post_publish_actions


def run_post_publish_actions(sender: type[Page], instance: Page, revision: Revision, **kwargs: Any) -> None:
    bundle = get_active_bundle_for_page(instance)

    registry = get_post_publish_actions()

    # TODO: Handle pages not in bundle.
    # For now, run synchronously.
    if bundle is None:
        for handler in registry.values():
            handler(instance, bundle)
        return

    for action_type, action_handler in registry.items():
        PostPublishAction.objects.update_or_create(
            page=instance,
            bundle=bundle,
            action_type=action_type,
            defaults={
                "status": PostPublishActionStatus.READY,
                "finished_at": None,
            },
        )

        handler = partial(
            run_action, action_type=action_type, action_handler=action_handler, page_id=instance.pk, bundle_id=bundle.pk
        )

        # In tests, on_commit doesn't work as expected due to the wrapping transaction. Instead, support bypassing it
        # and running the handler immediately.
        if settings.BUNDLE_POST_PUBLISH_ACTION_SUBMIT_ON_COMMIT:
            # NB: It assumed that if this is run inside a transaction, that the transaction closes when the page has
            # finished publishing. This ensures the thread's view is of a published page.
            transaction.on_commit(
                partial(
                    run_in_executor,
                    handler,
                ),
            )
        else:
            run_in_executor(handler)


def register_signal_handlers() -> None:
    page_published.connect(run_post_publish_actions)
