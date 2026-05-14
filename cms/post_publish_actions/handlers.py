from collections.abc import Callable
from functools import partial

from django.conf import settings
from django.db import transaction
from wagtail.models import Page

from cms.bundles.models import Bundle

from .executor import run_action, run_in_executor
from .models import PostPublishAction, PostPublishActionStatus, PostPublishActionType


def run_post_publish_action(
    action_type: PostPublishActionType, page: Page, bundle: Bundle | None, action_handler: Callable[[], None]
) -> None:
    # TODO: Handle pages not in bundle
    if bundle is None:
        action_handler()
        return

    PostPublishAction.objects.update_or_create(
        page=page,
        bundle=bundle,
        action_type=action_type,
        defaults={
            "status": PostPublishActionStatus.READY,
            "finished_at": None,
        },
    )

    handler = partial(
        run_action, action_type=action_type, action_handler=action_handler, page_id=page.pk, bundle_id=bundle.pk
    )

    # In tests, on_commit doesn't work as expected due to the wrapping transaction. Instead, support bypassing it and
    # running the handler immediately.
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
