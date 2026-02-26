from typing import TYPE_CHECKING, Any

from django.apps import apps
from django.db.models.signals import post_delete
from wagtail.signals import page_published, page_slug_changed, page_unpublished, published, unpublished

from cms.articles.models import ArticlesIndexPage
from cms.core.models import BasePage, ContactDetails, Definition
from cms.home.models import HomePage
from cms.methodology.models import MethodologyIndexPage
from cms.release_calendar.models import ReleaseCalendarIndex

from .cache import (
    purge_old_page_slugs_from_frontend_cache,
    purge_page_containing_snippet_from_cache,
    purge_page_from_frontend_cache,
)

if TYPE_CHECKING:
    from django.db.models import Model
    from wagtail.models import Page


def purge_published_page_from_frontend_cache(instance: Page, **kwargs: Any) -> None:
    purge_page_from_frontend_cache(instance)


def purge_unpublished_page_from_frontend_cache(instance: Page, **kwargs: Any) -> None:
    # note: this also covers page deletion
    # https://github.com/wagtail/wagtail/blob/228058b56775b126a91ecc4e4338366869513ea8/wagtail/signal_handlers.py#L31
    purge_page_from_frontend_cache(instance)


def purge_page_from_frontend_cache_after_slug_change(instance: Page, instance_before: Page, **kwargs: Any) -> None:
    purge_old_page_slugs_from_frontend_cache(instance, instance_before)


def purge_pages_containing_the_published_snippet_from_frontend_cache(instance: Model, **kwargs: Any) -> None:
    purge_page_containing_snippet_from_cache(instance)


def purge_pages_containing_the_unpublished_snippet_from_frontend_cache(instance: Model, **kwargs: Any) -> None:
    purge_page_containing_snippet_from_cache(instance)


def purge_pages_containing_the_deleted_snippet_from_frontend_cache(
    _sender: Model,
    instance: Model,
    **kwargs: Any,
) -> None:
    purge_page_containing_snippet_from_cache(instance)


def _get_tracked_page_models() -> set[Page]:
    """Returns a list of page models that are included in the front-end cache purging.

    We're excluding the following page types:
    - HomePage as it is not served by from Wagtail. TODO: remove when switching to do that
    - The Release Calendar, articles and methodology indexes are served by the Search service and has a short TTL
    """
    excluded_types = {ArticlesIndexPage, HomePage, MethodologyIndexPage, ReleaseCalendarIndex}
    return {model for model in apps.get_models() if issubclass(model, BasePage) and model not in excluded_types}


def register_signal_handlers() -> None:
    for model in _get_tracked_page_models():
        page_published.connect(purge_published_page_from_frontend_cache, sender=model)
        page_unpublished.connect(purge_unpublished_page_from_frontend_cache, sender=model)
        page_slug_changed.connect(purge_page_from_frontend_cache_after_slug_change, sender=model)

    for model in [ContactDetails, Definition]:
        published.connect(purge_pages_containing_the_unpublished_snippet_from_frontend_cache, sender=model)
        unpublished.connect(purge_pages_containing_the_unpublished_snippet_from_frontend_cache, sender=model)
        post_delete.connect(  # type: ignore[arg-type]
            purge_pages_containing_the_deleted_snippet_from_frontend_cache, sender=model
        )

    # FIXME when allowing to edit navigation
    # - Main Menu on publish, if in nav
    # - Footer menu on publish, if in nav
    # - Nav save, if there are changes

    # TODO
    # - page move
