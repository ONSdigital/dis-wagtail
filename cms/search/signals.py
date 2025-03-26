from django.apps import apps
from django.db.models.signals import post_delete
from django.dispatch import receiver
from wagtail.models import Page
from wagtail.signals import page_published, page_unpublished

from cms.settings.base import SEARCH_INDEX_EXCLUDED_PAGE_TYPES

from . import get_publisher

publisher = get_publisher()


@receiver(page_published)
def on_page_published(sender: "Page", instance: "Page", **kwargs: dict) -> None:  # pylint: disable=unused-argument
    """Called whenever a Wagtail Page is published (UI or code).
    instance is the published Page object.
    """
    if instance.__class__.__name__ not in SEARCH_INDEX_EXCLUDED_PAGE_TYPES:
        publisher.publish_created_or_updated(instance)


@receiver(page_unpublished)
def on_page_unpublished(sender: "Page", instance: "Page", **kwargs: dict) -> None:  # pylint: disable=unused-argument
    """Called whenever a Wagtail Page is unpublished (UI or code).
    instance is the unpublished Page object.
    """
    if instance.__class__.__name__ not in SEARCH_INDEX_EXCLUDED_PAGE_TYPES:
        publisher.publish_deleted(instance)


def on_page_deleted(sender: "Page", instance: "Page", **kwargs: dict) -> None:  # pylint: disable=unused-argument
    """Catches all subclass deletions of Wagtail's Page model.
    Only fires if the page is not in SEARCH_INDEX_EXCLUDED_PAGE_TYPES.
    """
    # Only proceed if `sender` is a subclass of Wagtail Page
    if instance.__class__.__name__ not in SEARCH_INDEX_EXCLUDED_PAGE_TYPES:
        publisher.publish_deleted(instance)


def connect_page_delete_signal() -> None:
    """Connect `on_page_deleted` to post_delete on `Page` and all its subclasses."""
    all_models = apps.get_models()
    for model in all_models:
        if issubclass(model, Page):
            post_delete.connect(on_page_deleted, sender=model, dispatch_uid=f"on_delete_{model._meta.label}")
