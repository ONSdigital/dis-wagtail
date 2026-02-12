from typing import TYPE_CHECKING, Any

from django.conf import settings
from django.shortcuts import redirect
from wagtail import hooks
from wagtail.admin import messages
from wagtail.log_actions import LogFormatter

from cms.themes.models import ThemePage

from .models import TopicPage
from .viewsets import (
    featured_series_page_chooser_viewset,
    highlighted_article_page_chooser_viewset,
    highlighted_methodology_page_chooser_viewset,
    series_with_headline_figures_chooser_viewset,
)

if TYPE_CHECKING:
    from django.http import HttpRequest, HttpResponse
    from wagtail.log_actions import LogActionRegistry
    from wagtail.models import ModelLogEntry, Page

    from .viewsets import (
        FeaturedSeriesPageChooserViewSet,
        HighlightedArticlePageChooserViewSet,
        HighlightedMethodologyPageChooserViewSet,
        SeriesWithHeadlineFiguresPageChooserViewSet,
    )


@hooks.register("register_admin_viewset")
def register_series_chooser_viewset() -> FeaturedSeriesPageChooserViewSet:
    return featured_series_page_chooser_viewset


@hooks.register("register_admin_viewset")
def register_highlighted_article_chooser_viewset() -> HighlightedArticlePageChooserViewSet:
    return highlighted_article_page_chooser_viewset


@hooks.register("register_admin_viewset")
def register_highlighted_methodology_chooser_viewset() -> HighlightedMethodologyPageChooserViewSet:
    return highlighted_methodology_page_chooser_viewset


@hooks.register("register_admin_viewset")
def register_series_with_headline_figures_chooser_viewset() -> SeriesWithHeadlineFiguresPageChooserViewSet:
    return series_with_headline_figures_chooser_viewset


@hooks.register("before_copy_page")
def before_create_page(request: HttpRequest, page: Page) -> HttpResponse | None:
    if settings.ENFORCE_EXCLUSIVE_TAXONOMY and page.specific_class in [TopicPage, ThemePage]:
        messages.warning(
            request,
            "Topic and theme pages cannot be duplicated as selected taxonomy needs to be unique for each page.",
        )
        return redirect("wagtailadmin_explore", page.get_parent().id)
    return None


@hooks.register("register_log_actions")
def register_topics_log_actions(actions: LogActionRegistry) -> None:
    @actions.register_action("topics.headline_figures_chooser.view")
    class ViewHeadlineFiguresChooser(LogFormatter):  # pylint: disable=unused-variable
        label = "View headline figures chooser"

        def format_message(self, log_entry: ModelLogEntry) -> Any:
            base_message = "Viewed headline figures in chooser"
            try:
                figure_ids = log_entry.data["figure_ids"]
                return f"{base_message}: {', '.join(figure_ids)}"
            except KeyError:
                return base_message
