from typing import TYPE_CHECKING, Any

from django.apps import apps
from wagtail.signals import page_published, page_unpublished, published, unpublished

if TYPE_CHECKING:
    from django.db.models import Model
    from wagtail.models import Page


def page_published_signal_handler(instance: Page, **kwargs: Any) -> None:
    from .cache import purge_page_from_frontend_cache  # pylint: disable=import-outside-toplevel

    purge_page_from_frontend_cache(instance)


def page_unpublished_signal_handler(instance: Page, **kwargs: Any) -> None:
    from .cache import purge_page_from_frontend_cache  # pylint: disable=import-outside-toplevel

    purge_page_from_frontend_cache(instance)


def snippet_published(instance: Model, **kwargs: Any) -> None:
    from .cache import purge_page_containing_snippet_from_cache  # pylint: disable=import-outside-toplevel

    purge_page_containing_snippet_from_cache(instance)


def snippet_unpublished(instance: Model, **kwargs: Any) -> None:
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

    for model in _get_tracked_snippets():
        published.connect(snippet_unpublished, sender=model)
        unpublished.connect(snippet_unpublished, sender=model)

    # FIXME when allowing to edit navigation
    # - Main Menu on publish, if in nav
    # - Footer menu on publish, if in nav
    # - Nav save, if there are changes

    # TODO
    # - page move
    # - page deletion (page, children, special paths)
    # - page slug change (page, children, special paths)
