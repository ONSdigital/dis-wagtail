import logging
from functools import cache
from typing import Any

from django.conf import settings
from django.db.models.signals import post_delete
from django.dispatch import receiver
from wagtail.models import Page
from wagtail.signals import page_published, page_slug_changed, page_unpublished, post_page_move

from cms.search.publishers import KafkaPublisher, LogPublisher
from cms.search.utils import get_model_by_name

logger = logging.getLogger(__name__)


@cache
def get_publisher() -> KafkaPublisher | LogPublisher:
    """Return the configured publisher backend."""
    backend = settings.SEARCH_INDEX_PUBLISHER_BACKEND
    if backend == "kafka":
        return KafkaPublisher()
    return LogPublisher()


@receiver(page_published)
def on_page_published(sender: "type[Page]", instance: "Page", **kwargs: Any) -> None:  # pylint: disable=unused-argument
    """Called whenever a Wagtail Page is published (UI or code).
    instance is the published Page object.
    """
    if (
        instance.specific_class.__name__ not in settings.SEARCH_INDEX_EXCLUDED_PAGE_TYPES
        and not instance.get_view_restrictions().exists()
    ):
        get_publisher().publish_created_or_updated(instance)


@receiver(page_unpublished)
def on_page_unpublished(sender: "type[Page]", instance: "Page", **kwargs: Any) -> None:  # pylint: disable=unused-argument
    """Called whenever a Wagtail Page is unpublished (UI or code).
    instance is the unpublished Page object.
    """
    if (
        settings.CMS_SEARCH_NOTIFY_ON_DELETE_OR_UNPUBLISH
        and instance.specific_class.__name__ not in settings.SEARCH_INDEX_EXCLUDED_PAGE_TYPES
        and not instance.get_view_restrictions().exists()
    ):
        get_publisher().publish_deleted(instance)


@receiver(post_delete, sender=Page)
def on_page_deleted(sender: "type[Page]", instance: "Page", **kwargs: Any) -> None:  # pylint: disable=unused-argument
    """Catches all subclass deletions of Wagtail's Page model.
    Only fires if the page is published and not in SEARCH_INDEX_EXCLUDED_PAGE_TYPES.
    """
    # Only proceed if `sender` is a subclass of Wagtail Page and the page is published
    if (
        settings.CMS_SEARCH_NOTIFY_ON_DELETE_OR_UNPUBLISH
        and instance.live
        and instance.specific_class.__name__ not in settings.SEARCH_INDEX_EXCLUDED_PAGE_TYPES
        and not instance.get_view_restrictions().exists()
    ):
        get_publisher().publish_deleted(instance)


@receiver(page_slug_changed)
def on_page_slug_changed(sender: "type[Page]", instance: "Page", instance_before: "Page", **kwargs: Any) -> None:  # pylint: disable=unused-argument
    """Called after a Wagtail Page's slug is changed.
    "instance" is the updated Page object, "instance_before" is the Page object before the slug change.
    We need to update the search index for pages descendants whose URL paths have changed as a result.
    This handler does not update search for the instance itself, as that is handled by the page_published signal.
    """
    if instance.get_view_restrictions().exists():
        # If the page has view restrictions then it and all descendants are excluded from search indexing,
        # we can short-circuit
        return
    old_url_path = instance_before.url_path
    new_url_path = instance.url_path
    _update_page_descendant_paths(instance, old_url_path, new_url_path)


@receiver(post_page_move)
def on_page_moved(sender: "type[Page]", instance: "Page", **kwargs: Any) -> None:  # pylint: disable=unused-argument
    """Called after a Wagtail Page is moved in the tree.
    "instance" is the moved Page object.
    We use the publish_created_or_updated method to update search for the moved page and any of its non-excluded
    descendants, which will also be affected by the move.
    """
    if kwargs["url_path_before"] == kwargs["url_path_after"]:
        # No change in URL path, no need to update search index of the instance or descendants
        return
    if instance.get_view_restrictions().exists():
        # Pages with view restrictions should not be exposed in search
        # this is inherited by descendants, so nothing more to do
        return
    old_url_path: str = kwargs["url_path_before"]
    new_url_path: str = kwargs["url_path_after"]
    if instance.live and instance.specific_class.__name__ not in settings.SEARCH_INDEX_EXCLUDED_PAGE_TYPES:
        try:
            get_publisher().publish_created_or_updated(instance.specific_deferred, old_url_path=old_url_path)
        except Exception:  # pylint: disable=broad-except
            logger.exception(
                "Failed to publish moved page to search index",
                extra={"page_id": instance.id, "old_url_path": old_url_path, "new_url_path": new_url_path},
            )
    _update_page_descendant_paths(instance, old_url_path, new_url_path)


def _update_page_descendant_paths(instance: "Page", old_url_path: str, new_url_path: str) -> None:
    """Update the search index for all descendants of a page whose URL paths have changed."""
    for descendant in (
        instance.get_descendants()
        .filter(live=True)
        .public()
        .not_exact_type(*(get_model_by_name(page_type) for page_type in settings.SEARCH_INDEX_EXCLUDED_PAGE_TYPES))
        .specific(defer=True)
    ):
        old_descendant_path = build_old_descendant_path(
            parent_page=instance,
            descendant_page=descendant,
            parent_path_before=old_url_path,
            parent_path_after=new_url_path,
        )

        try:
            get_publisher().publish_created_or_updated(descendant, old_url_path=old_descendant_path)
        except Exception:  # pylint: disable=broad-except
            logger.exception(
                "Failed to publish updated descendant page to search index",
                extra={"page_id": descendant.id, "old_url_path": old_url_path, "new_url_path": new_url_path},
            )


def build_old_descendant_path(
    *, parent_page: "Page", descendant_page: "Page", parent_path_before: str, parent_path_after: str
) -> str | None:
    """Build the old URL path for a moved descendant page."""
    if descendant_page.url_path.startswith(parent_path_after):
        # We expect the old URL path to be derivable from the new URL path of the parent and the descendant
        # Strip the url_path_after prefix from the descendant's url_path and prepend the url_path_before
        return f"{parent_path_before}{descendant_page.url_path[len(parent_path_after) :]}"

    logger.error(
        "Found mismatching descendant page url_path while handling page move, cannot build old URL "
        "path to remove from search index.",
        extra={
            "parent_url_path": parent_path_after,
            "descendant_url_path": descendant_page.url_path,
            "parent_page": parent_page.id,
            "descendant_page": descendant_page.id,
        },
    )
    return None
