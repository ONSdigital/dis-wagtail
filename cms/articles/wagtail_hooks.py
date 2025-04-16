from typing import TYPE_CHECKING

from wagtail import hooks
from wagtail.admin import messages

from cms.articles.models import StatisticalArticlePage

if TYPE_CHECKING:
    from django.http import HttpRequest
    from wagtail.models import Page


@hooks.register("before_create_page")
def before_create_page(
    request: "HttpRequest",
    parent_page: "Page",
    page_class: type["Page"],
) -> None:
    if page_class == StatisticalArticlePage and parent_page.get_latest():
        # Display message - the actual prepopulation is done in the signal handler
        messages.info(
            request,
            "This page has been prepopulated with the content from the latest page in the series.",
        )
