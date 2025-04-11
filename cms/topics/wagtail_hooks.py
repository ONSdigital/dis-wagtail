from typing import TYPE_CHECKING

from wagtail import hooks

from .viewsets import (
    featured_series_page_chooser_viewset,
    highlighted_article_page_chooser_viewset,
    highlighted_methodology_page_chooser_viewset,
    series_with_headline_figures_chooser_viewset,
)

if TYPE_CHECKING:
    from .viewsets import (
        FeaturedSeriesPageChooserViewSet,
        HighlightedArticlePageChooserViewSet,
        HighlightedMethodologyPageChooserViewSet,
        SeriesWithHeadlineFiguresPageChooserViewSet,
    )


@hooks.register("register_admin_viewset")
def register_series_chooser_viewset() -> "FeaturedSeriesPageChooserViewSet":
    return featured_series_page_chooser_viewset


@hooks.register("register_admin_viewset")
def register_highlighted_article_chooser_viewset() -> "HighlightedArticlePageChooserViewSet":
    return highlighted_article_page_chooser_viewset


@hooks.register("register_admin_viewset")
def register_highlighted_methodology_chooser_viewset() -> "HighlightedMethodologyPageChooserViewSet":
    return highlighted_methodology_page_chooser_viewset


@hooks.register("register_admin_viewset")
def register_series_with_headline_figures_chooser_viewset() -> "SeriesWithHeadlineFiguresPageChooserViewSet":
    return series_with_headline_figures_chooser_viewset
