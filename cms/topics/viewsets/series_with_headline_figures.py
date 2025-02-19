from typing import TYPE_CHECKING, ClassVar

from wagtail.admin.ui.tables import Column, DateColumn
from wagtail.admin.ui.tables.pages import PageStatusColumn
from wagtail.admin.views.generic.chooser import ChooseResultsView, ChooseView
from wagtail.admin.viewsets.chooser import ChooserViewSet
from wagtail.coreutils import resolve_model_string

from cms.articles.models import ArticleSeriesPage

if TYPE_CHECKING:
    from wagtail.query import PageQuerySet


__all__ = ["SeriesWithHeadlineFiguresPageChooserViewSet", "series_with_headline_figures_chooser_viewset"]


class SeriesWithHeadlineFiguresChooserMixin:
    model_class: ArticleSeriesPage

    def get_object_list(self) -> "PageQuerySet[ArticleSeriesPage]":
        topic_page_id = self.request.GET.get("topic_page_id")
        if not topic_page_id:
            return ArticleSeriesPage.objects.none()

        series_pages = ArticleSeriesPage.objects.all().defer_streamfields().order_by("path")
        # using this rather than inline import to placate pyright complaining about cyclic imports
        topic_page_model = resolve_model_string("topics.TopicPage")
        try:
            series_pages = series_pages.child_of(topic_page_model.objects.get(pk=topic_page_id))
        except topic_page_model.DoesNotExist:
            series_pages = series_pages.none()

        filtered_series = []
        for series_page in series_pages:
            latest_article = series_page.get_latest()
            if latest_article and latest_article.headline_figures.raw_data:
                filtered_series.append(series_page)

        series_pages = series_pages.filter(pk__in=filtered_series)
        return series_pages

    @property
    def columns(self) -> list["Column"]:
        return [
            self.title_column,  # type: ignore[attr-defined]
            Column("parent", label="Topic", accessor="get_parent"),
            DateColumn(
                "updated",
                label="Updated",
                width="12%",
                accessor="latest_revision_created_at",
            ),
            PageStatusColumn("status", label="Status", width="12%"),
        ]


class SeriesWithHeadlineFiguresChooseView(SeriesWithHeadlineFiguresChooserMixin, ChooseView): ...


class SeriesWithHeadlineFiguresChooseResultsView(SeriesWithHeadlineFiguresChooserMixin, ChooseResultsView): ...


class SeriesWithHeadlineFiguresPageChooserViewSet(ChooserViewSet):
    model = ArticleSeriesPage
    choose_view_class = SeriesWithHeadlineFiguresChooseView
    choose_results_view_class = SeriesWithHeadlineFiguresChooseResultsView
    register_widget = False
    choose_one_text = "Choose Article Series page"
    choose_another_text = "Choose another Article Series page"
    edit_item_text = "Edit Article Series page"
    preserve_url_parameters: ClassVar[list[str]] = ["multiple", "topic_page_id"]


series_with_headline_figures_chooser_viewset = SeriesWithHeadlineFiguresPageChooserViewSet(
    "topic_series_with_headline_figures_chooser"
)
