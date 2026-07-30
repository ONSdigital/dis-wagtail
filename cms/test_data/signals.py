from collections.abc import Callable, Generator, Iterable
from contextlib import contextmanager

from django.db.models import Model
from django.db.models.signals import post_delete, post_save
from django.dispatch import Signal
from modelsearch.signal_handlers import post_save_signal_handler
from wagtail.models import Page
from wagtail.signal_handlers import update_reference_index_on_save
from wagtail.signals import page_published, page_slug_changed, page_unpublished, post_page_move

from cms.search.signal_handlers import (
    on_page_deleted,
    on_page_moved,
    on_page_published,
    on_page_slug_changed,
    on_page_unpublished,
)

Receiver = tuple[Signal, Callable, type[Model] | None]


@contextmanager
def disconnect_receivers(receivers: Iterable[Receiver]) -> Generator[None]:
    """Disconnect receivers for duration of context, then reconnect."""
    disconnected: list[Receiver] = []

    for signal, receiver, sender in receivers:
        if signal.disconnect(receiver, sender=sender):
            disconnected.append((signal, receiver, sender))

    try:
        yield
    finally:
        for signal, receiver, sender in disconnected:
            signal.connect(receiver, sender=sender)


def index_receivers(models: Iterable[type[Model]]) -> list[Receiver]:
    return [
        (post_save, receiver, model)
        for model in models
        for receiver in (post_save_signal_handler, update_reference_index_on_save)
    ]


def search_publisher_receivers() -> list[Receiver]:
    return [
        (page_published, on_page_published, None),
        (page_unpublished, on_page_unpublished, None),
        (page_slug_changed, on_page_slug_changed, None),
        (post_page_move, on_page_moved, None),
        (post_delete, on_page_deleted, Page),
    ]
