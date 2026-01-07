from typing import TYPE_CHECKING, Union

from django.http import HttpResponseRedirect
from django.shortcuts import redirect
from django.urls import include, path
from wagtail import hooks
from wagtail.admin import messages

from cms.articles import admin_urls
from cms.articles.models import ArticleSeriesPage, StatisticalArticlePage

if TYPE_CHECKING:
    from django.http import HttpRequest
    from django.urls import URLPattern
    from django.urls.resolvers import URLResolver
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


@hooks.register("before_delete_page")
def before_delete_page(request: "HttpRequest", page: "Page") -> HttpResponseRedirect | None:
    if request.method == "POST":
        if page.specific_class == StatisticalArticlePage and page.specific.figures_used_by_ancestor:
            messages.warning(
                request,
                "This page cannot be deleted because it contains headline figures that are referenced elsewhere.",
            )
            # Redirect to the delete page (the same page) to prevent delete action
            # See: https://docs.wagtail.org/en/latest/reference/hooks.html#before-delete-page
            return redirect("wagtailadmin_pages:delete", page.pk)
        if (
            page.specific_class == ArticleSeriesPage
            and (latest := page.get_latest())
            and latest.figures_used_by_ancestor
        ):
            message = (
                "This page cannot be deleted because one or more of its children contain headline figures"
                " that are referenced elsewhere."
            )
            messages.warning(request, message)
            return redirect("wagtailadmin_pages:delete", page.pk)

    return None


@hooks.register("register_admin_urls")
def register_admin_urls() -> list[Union["URLPattern", "URLResolver"]]:
    """Registers the admin urls for Articles.

    @see https://docs.wagtail.org/en/stable/reference/hooks.html#register-admin-urls.
    """
    return [path("articles/", include(admin_urls))]
