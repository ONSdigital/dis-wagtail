from collections.abc import Generator
from contextlib import contextmanager
from contextvars import ContextVar
from typing import TYPE_CHECKING, Any

from wagtail.models import Page
from wagtail.signals import page_published

from .utils import run_post_publish_actions_for

if TYPE_CHECKING:
    from cms.bundles.models import Bundle

_publishing_bundle: ContextVar[Bundle | None] = ContextVar("_publishing_bundle", default=None)


@contextmanager
def enqueue_post_publish_actions_for_bundle(bundle: Bundle) -> Generator[None]:
    """While active, page_published signals will enqueue post-publish actions for the given bundle instead of
    running synchronously.
    """
    context_bundle = _publishing_bundle.set(bundle)

    try:
        yield
    finally:
        _publishing_bundle.reset(context_bundle)


def run_post_publish_actions_handler(sender: type[Page], instance: Page, **kwargs: Any) -> None:  # pylint: disable=unused-argument
    run_post_publish_actions_for(instance, _publishing_bundle.get())


def register_signal_handlers() -> None:
    page_published.connect(run_post_publish_actions_handler, dispatch_uid="run_post_publish_actions_handler")
