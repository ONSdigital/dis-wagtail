from typing import TYPE_CHECKING

from wagtail import hooks
from wagtail.models import Page

from . import get_publisher

if TYPE_CHECKING:
    from django.http import HttpRequest

publisher = get_publisher()


def _should_exclude_page(page: Page) -> bool:
    """Return True if the page should be excluded from publishing."""
    return page.__class__.__name__ in EXCLUDED_PAGE_TYPES


@hooks.register("after_publish_page")
def page_published(request: "HttpRequest", page: Page) -> None:
    """This hook is called after a page is published from the Wagtail admin."""
    if _should_exclude_page(page):
        return
    publisher.publish_created_or_updated(page)


@hooks.register("after_unpublish_page")
def page_unpublished(request: "HttpRequest", page: Page) -> None:
    """This hook is called after a page is unpublished from the Wagtail admin."""
    if _should_exclude_page(page):
        return
    publisher.publish_deleted(page)


EXCLUDED_PAGE_TYPES = (
    "HomePage",
    "ArticleSeriesPage",
    "ReleaseCalendarIndex",
    "ThemePage",
    "TopicPage",
)
