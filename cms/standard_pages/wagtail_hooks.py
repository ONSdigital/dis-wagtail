from wagtail import hooks

from cms.standard_pages.models import CookiesPage


@hooks.register("construct_explorer_page_queryset")
def hide_cookies_page(_parent_page, pages, _request):
    """The cookies page is static, so hide it from the page explorer."""
    pages = pages.not_type(CookiesPage)
    return pages
