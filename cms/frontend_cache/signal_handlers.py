from typing import TYPE_CHECKING, Any

from django.apps import apps
from django.db.models.signals import post_delete
from wagtail.signals import page_published, page_slug_changed, page_unpublished, published, unpublished

if TYPE_CHECKING:
    from django.db.models import Model
    from wagtail.models import Page


def page_published_signal_handler(instance: Page, **kwargs: Any) -> None:
    from .cache import purge_page_from_frontend_cache  # pylint: disable=import-outside-toplevel

    purge_page_from_frontend_cache(instance)


def page_unpublished_signal_handler(instance: Page, **kwargs: Any) -> None:
    # note: this also covers page deletion
    # https://github.com/wagtail/wagtail/blob/228058b56775b126a91ecc4e4338366869513ea8/wagtail/signal_handlers.py#L31
    from .cache import purge_page_from_frontend_cache  # pylint: disable=import-outside-toplevel

    purge_page_from_frontend_cache(instance)


def page_slug_changed_signal_handler(instance: Page, instance_before: Page, **kwargs: Any) -> None:
    from cms.frontend_cache.cache import (  # pylint: disable=import-outside-toplevel
        purge_old_page_slugs_from_frontend_cache,
    )

    purge_old_page_slugs_from_frontend_cache(instance, instance_before)


def snippet_published(instance: Model, **kwargs: Any) -> None:
    from .cache import purge_page_containing_snippet_from_cache  # pylint: disable=import-outside-toplevel

    purge_page_containing_snippet_from_cache(instance)


def snippet_unpublished(instance: Model, **kwargs: Any) -> None:
    from .cache import purge_page_containing_snippet_from_cache  # pylint: disable=import-outside-toplevel

    purge_page_containing_snippet_from_cache(instance)


def snippet_deleted(sender: Model, instance: Model, **kwargs: Any) -> None:  # pylint: disable=unused-argument
    from .cache import purge_page_containing_snippet_from_cache  # pylint: disable=import-outside-toplevel

    purge_page_containing_snippet_from_cache(instance)


def _get_indexed_page_models() -> set[Page]:
    # inlined to allow app instantiation
    from cms.core.models import BasePage  # pylint: disable=import-outside-toplevel

    # pylint: disable=invalid-name
    ArticlesIndexPage = apps.get_model("articles", "ArticlesIndexPage")
    HomePage = apps.get_model("home", "HomePage")
    MethodologyIndexPage = apps.get_model("methodology", "MethodologyIndexPage")
    ReleaseCalendarIndex = apps.get_model("release_calendar", "ReleaseCalendarIndex")
    # pylint: enable=invalid-name

    # TODO: remove HomePage from the list when serving it from Wagtail
    # The Release Calendar, articles and methodology indexes are served by the Search service and has a short TTL
    excluded_types = {ArticlesIndexPage, HomePage, MethodologyIndexPage, ReleaseCalendarIndex}
    return {model for model in apps.get_models() if issubclass(model, BasePage) and model not in excluded_types}


def _get_tracked_snippets() -> set[Model]:
    return {
        apps.get_model("core", "ContactDetails"),  # type: ignore[arg-type]
        apps.get_model("core", "Definition"),  # type: ignore[arg-type]
    }


def register_signal_handlers() -> None:
    for model in _get_indexed_page_models():
        page_published.connect(page_published_signal_handler, sender=model)
        page_unpublished.connect(page_unpublished_signal_handler, sender=model)
        page_slug_changed.connect(page_slug_changed_signal_handler, sender=model)

    for model in _get_tracked_snippets():
        published.connect(snippet_unpublished, sender=model)
        unpublished.connect(snippet_unpublished, sender=model)
        post_delete.connect(snippet_deleted, sender=model)  # type: ignore[arg-type]

    # FIXME when allowing to edit navigation
    # - Main Menu on publish, if in nav
    # - Footer menu on publish, if in nav
    # - Nav save, if there are changes

    # TODO
    # - page move
    # - page slug change (page, children, special paths)
