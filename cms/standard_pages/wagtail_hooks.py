from typing import TYPE_CHECKING

from wagtail import hooks

from cms.standard_pages.models import CookiesPage

if TYPE_CHECKING:
    from django.http import HttpRequest
    from wagtail.models import Page
    from wagtail.query import PageQuerySet


@hooks.register("construct_explorer_page_queryset")
def hide_cookies_page(_parent_page: "Page", pages: "PageQuerySet", _request: "HttpRequest") -> "PageQuerySet":
    """The cookies page is static, so hide it from the page explorer."""
    pages = pages.not_type(CookiesPage)
    return pages
