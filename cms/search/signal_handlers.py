from functools import cache

from django.conf import settings
from django.db.models.signals import post_delete
from django.dispatch import receiver
from wagtail.models import Page
from wagtail.signals import page_published, page_unpublished, post_page_move

from .publishers import KafkaPublisher, LogPublisher


@cache
def get_publisher() -> KafkaPublisher | LogPublisher:
    """Return the configured publisher backend."""
    backend = settings.SEARCH_INDEX_PUBLISHER_BACKEND
    if backend == "kafka":
        return KafkaPublisher()
    return LogPublisher()


@receiver(page_published)
def on_page_published(sender: "type[Page]", instance: "Page", **kwargs: dict) -> None:  # pylint: disable=unused-argument
    """Called whenever a Wagtail Page is published (UI or code).
    instance is the published Page object.
    """
    if instance.specific_class.__name__ not in settings.SEARCH_INDEX_EXCLUDED_PAGE_TYPES:
        get_publisher().publish_created_or_updated(instance)


@receiver(page_unpublished)
def on_page_unpublished(sender: "type[Page]", instance: "Page", **kwargs: dict) -> None:  # pylint: disable=unused-argument
    """Called whenever a Wagtail Page is unpublished (UI or code).
    instance is the unpublished Page object.
    """
    if (
        settings.CMS_SEARCH_NOTIFY_ON_DELETE_OR_UNPUBLISH
        and instance.specific_class.__name__ not in settings.SEARCH_INDEX_EXCLUDED_PAGE_TYPES
    ):
        get_publisher().publish_deleted(instance)


@receiver(post_delete, sender=Page)
def on_page_deleted(sender: "type[Page]", instance: "Page", **kwargs: dict) -> None:  # pylint: disable=unused-argument
    """Catches all subclass deletions of Wagtail's Page model.
    Only fires if the page is published and not in SEARCH_INDEX_EXCLUDED_PAGE_TYPES.
    """
    # Only proceed if `sender` is a subclass of Wagtail Page and the page is published
    if (
        settings.CMS_SEARCH_NOTIFY_ON_DELETE_OR_UNPUBLISH
        and instance.live
        and instance.specific_class.__name__ not in settings.SEARCH_INDEX_EXCLUDED_PAGE_TYPES
    ):
        get_publisher().publish_deleted(instance)


@receiver(post_page_move)
def on_page_moved(sender: "type[Page]", instance: "Page", **kwargs: dict) -> None:  # pylint: disable=unused-argument
    """Called whenever a Wagtail Page is moved in the tree (UI or code).
    instance is the moved Page object.
    We use the publish_created_or_updated method to update search for the moved page and any of it's non-excluded
    descendants, which will also be affected by the move.
    """
    if kwargs["url_path_before"] == kwargs["url_path_after"]:
        # No change in URL path, no need to update search index of the instance or descendants
        return
    for moved_page in instance.get_descendants(inclusive=True):  # inclusive=True includes instance itself
        if moved_page.live and moved_page.specific_class.__name__ not in settings.SEARCH_INDEX_EXCLUDED_PAGE_TYPES:
            get_publisher().publish_created_or_updated(moved_page.specific_deferred)
