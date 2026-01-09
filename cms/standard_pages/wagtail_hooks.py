from typing import TYPE_CHECKING

from django.core.exceptions import PermissionDenied
from wagtail import hooks

from cms.standard_pages.models import CookiesPage

if TYPE_CHECKING:
    from django.http import HttpRequest
    from wagtail.models import Page
    from wagtail.query import PageQuerySet


@hooks.register("construct_explorer_page_queryset")
def hide_cookies_page(_parent_page: Page, pages: PageQuerySet, _request: HttpRequest) -> PageQuerySet:
    """The cookies page is static, so hide it from the page explorer."""
    return pages.not_type(CookiesPage)


def deny_for_cookies_page(page: Page) -> None:
    if isinstance(page, CookiesPage):
        raise PermissionDenied


@hooks.register("before_edit_page")
def before_edit_page(_request: HttpRequest, page: Page) -> None:
    """Don't allow users to edit the cookies pages."""
    deny_for_cookies_page(page)


@hooks.register("before_create_page")
def before_create_page(_request: HttpRequest, _parent_page: Page, page_class: type[Page]) -> None:
    """Don't allow users to create another cookies page."""
    if page_class == CookiesPage:
        raise PermissionDenied


@hooks.register("before_delete_page")
def before_delete_page(_request: HttpRequest, page: Page) -> None:
    """Don't allow users to delete the cookies pages."""
    deny_for_cookies_page(page)


@hooks.register("before_convert_alias_page")
def before_convert_alias_page(_request: HttpRequest, page: Page) -> None:
    """Don't allow users to convert the cookies page alias to a real page."""
    deny_for_cookies_page(page)


@hooks.register("before_publish_page")
def before_publish_page(_request: HttpRequest, page: Page) -> None:
    """Don't allow users to publish the cookies pages."""
    deny_for_cookies_page(page)


@hooks.register("before_unpublish_page")
def before_unpublish_page(_request: HttpRequest, page: Page) -> None:
    """Don't allow users to unpublish the cookies pages."""
    deny_for_cookies_page(page)


@hooks.register("before_move_page")
def before_move_page(_request: HttpRequest, page: Page, _destination_page: Page) -> None:
    """Don't allow users to move the cookies pages."""
    deny_for_cookies_page(page)
