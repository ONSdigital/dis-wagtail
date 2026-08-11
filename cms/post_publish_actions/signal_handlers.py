from collections.abc import Generator
from contextlib import contextmanager
from typing import Any

from asgiref.local import Local
from wagtail.models import Page
from wagtail.signals import page_published

from .utils import run_post_publish_actions_for

_suppress_post_publish_actions_signal = Local()


@contextmanager
def suppress_post_publish_actions_signal() -> Generator[None]:
    previous_value = getattr(_suppress_post_publish_actions_signal, "value", None)

    try:
        _suppress_post_publish_actions_signal.value = True
        yield
    finally:
        if previous_value is None:
            del _suppress_post_publish_actions_signal.value
        else:
            _suppress_post_publish_actions_signal.value = previous_value


def run_post_publish_actions_handler(sender: type[Page], instance: Page, **kwargs: Any) -> None:  # pylint: disable=unused-argument
    from cms.bundles.utils import get_active_bundle_for_page  # pylint: disable=import-outside-toplevel

    if getattr(_suppress_post_publish_actions_signal, "value", None):
        return

    # NB: If the bundle is already marked "published", this may return None.
    bundle = get_active_bundle_for_page(instance)

    run_post_publish_actions_for(instance, bundle)


def register_signal_handlers() -> None:
    page_published.connect(run_post_publish_actions_handler)
