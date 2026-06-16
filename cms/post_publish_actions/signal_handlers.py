from typing import Any

from wagtail.models import Page, Revision
from wagtail.signals import page_published

from cms.bundles.utils import get_active_bundle_for_page

from .models import PostPublishAction, PostPublishActionStatus
from .registry import get_post_publish_actions


def run_post_publish_actions(sender: type[Page], instance: Page, revision: Revision, **kwargs: Any) -> None:  # pylint: disable=unused-argument
    bundle = get_active_bundle_for_page(instance)

    registry = get_post_publish_actions()

    # TODO: Handle pages not in bundle.
    # For now, run synchronously.
    if bundle is None:
        for handler in registry.values():
            handler(instance, bundle)
        return

    for action_type in registry:
        action, _created = PostPublishAction.objects.update_or_create(
            page=instance,
            bundle=bundle,
            action_type=action_type,
            defaults={
                "status": PostPublishActionStatus.READY,
                "finished_at": None,
            },
        )

        action.enqueue()


def register_signal_handlers() -> None:
    page_published.connect(run_post_publish_actions)
