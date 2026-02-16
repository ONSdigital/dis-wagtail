from typing import TYPE_CHECKING, Any

from django.apps import apps
from wagtail.signals import page_published, page_unpublished

if TYPE_CHECKING:
    from wagtail.models import Page


def page_published_signal_handler(instance: Page, **kwargs: Any) -> None:
    from .cache import purge_page_from_frontend_cache  # pylint: disable=import-outside-toplevel

    purge_page_from_frontend_cache(instance)


def page_unpublished_signal_handler(instance: Page, **kwargs: Any) -> None:
    from .cache import purge_page_from_frontend_cache  # pylint: disable=import-outside-toplevel

    purge_page_from_frontend_cache(instance)


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


def register_signal_handlers() -> None:
    for model in _get_indexed_page_models():
        page_published.connect(page_published_signal_handler, sender=model)
        page_unpublished.connect(page_unpublished_signal_handler, sender=model)

    # TODO
    # - Main Menu on publish, if in nav
    # - Footer menu on publish, if in nav
    # - Nav save, if there are changes
    # - Contact Details on publish, all linked published pages
    # - Definitions on publish, all linked published pages
