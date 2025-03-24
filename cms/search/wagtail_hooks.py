from typing import TYPE_CHECKING

from wagtail import hooks

from cms.settings.base import EXCLUDED_PAGE_TYPES

from . import get_publisher

if TYPE_CHECKING:
    from django.http import HttpRequest
    from wagtail.models import Page

publisher = get_publisher()


@hooks.register("after_publish_page")
def page_published(request: "HttpRequest", page: "Page") -> None:
    """This hook is called after a page is published, either via the Wagtail admin UI or programmatically.

    Wagtail hook documentation: https://docs.wagtail.io/en/stable/reference/hooks.html#after-publish-page
    """
    if page.__class__.__name__ not in EXCLUDED_PAGE_TYPES:
        publisher.publish_created_or_updated(page)


@hooks.register("after_unpublish_page")
def page_unpublished(request: "HttpRequest", page: "Page") -> None:
    """This hook is called after a page is unpublished, either via the Wagtail admin UI or programmatically.

    Wagtail hook documentation: https://docs.wagtail.org/en/stable/reference/hooks.html#after-unpublish-page
    """
    if page.__class__.__name__ not in EXCLUDED_PAGE_TYPES:
        publisher.publish_deleted(page)
