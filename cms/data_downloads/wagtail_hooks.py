from typing import TYPE_CHECKING

from django.urls import include, path
from wagtail import hooks

from cms.data_downloads import urls

if TYPE_CHECKING:
    from django.urls import URLPattern
    from django.urls.resolvers import URLResolver


@hooks.register("register_admin_urls")
def register_data_download_urls() -> list[URLPattern | URLResolver]:
    """Registers the admin URLs for data downloads.

    @see https://docs.wagtail.org/en/stable/reference/hooks.html#register-admin-urls.
    """
    return [path("data-downloads/", include(urls))]
