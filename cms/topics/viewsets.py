from typing import TYPE_CHECKING, ClassVar

from wagtail.admin.ui.tables import Column, DateColumn
from wagtail.admin.ui.tables.pages import PageStatusColumn
from wagtail.admin.views.generic.chooser import ChooseResultsView, ChooseView
from wagtail.admin.viewsets.chooser import ChooserViewSet
from wagtail.coreutils import resolve_model_string

from cms.articles.models import ArticleSeriesPage, StatisticalArticlePage
from cms.methodology.models import MethodologyPage

if TYPE_CHECKING:
    from wagtail.models import Page
    from wagtail.query import PageQuerySet


class FeaturedSeriesPageChooseViewMixin:
    model_class: ArticleSeriesPage

    def get_object_list(self) -> "PageQuerySet[ArticleSeriesPage]":
        return ArticleSeriesPage.objects.all().order_by("path")

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


class FeaturedSeriesPageChooseView(FeaturedSeriesPageChooseViewMixin, ChooseView): ...


class FeaturedSeriesPageChooseResultsView(FeaturedSeriesPageChooseViewMixin, ChooseResultsView): ...


class FeaturedSeriesPageChooserViewSet(ChooserViewSet):
    model = ArticleSeriesPage
    choose_view_class = FeaturedSeriesPageChooseView
    choose_results_view_class = FeaturedSeriesPageChooseResultsView
    register_widget = False
    choose_one_text = "Choose Article Series page"
    choose_another_text = "Choose another Article Series page"
    edit_item_text = "Edit Article Series page"


class HighlightedChildPageChooseViewMixin:
    def get_object_list(self) -> "PageQuerySet[Page]":
        model_class: StatisticalArticlePage | MethodologyPage = self.model_class  # type: ignore[attr-defined]
        pages: PageQuerySet[Page] = model_class.objects.all().defer_streamfields()
        if topic_page_id := self.request.GET.get("topic_page_id"):  # type: ignore[attr-defined]
            # using this rather than inline import to placate pyright complaining about cyclic imports
            topic_page_model = resolve_model_string("topics.TopicPage")
            try:
                pages = pages.descendant_of(topic_page_model.objects.get(pk=topic_page_id))
            except topic_page_model.DoesNotExist:
                pages = pages.none()
        else:
            # when adding new pages.
            pages = pages.none()

        if model_class == StatisticalArticlePage:
            pages = pages.order_by("-release_date")

        if model_class == MethodologyPage:
            pages = pages.order_by("-publication_date")
        return pages

    @property
    def columns(self) -> list["Column"]:
        title_column = self.title_column  # type: ignore[attr-defined]
        title_column.accessor = "get_admin_display_title"
        return [
            title_column,
            Column(
                "release_date",
                label="Release date",
                width="12%",
                accessor="release_date",
            ),
            PageStatusColumn("status", label="Status", width="12%"),
        ]


class HighlightedPagePageChooseView(HighlightedChildPageChooseViewMixin, ChooseView): ...


class HighlightedPagePageChooseResultsView(HighlightedChildPageChooseViewMixin, ChooseResultsView): ...


class BaseHighlightedChildrenViewSet(ChooserViewSet):
    choose_view_class = HighlightedPagePageChooseView
    choose_results_view_class = HighlightedPagePageChooseResultsView
    register_widget = False
    preserve_url_parameters: ClassVar[list[str]] = ["multiple", "topic_page_id"]
    icon = "doc-empty-inverse"


class HighlightedArticlePageChooserViewSet(BaseHighlightedChildrenViewSet):
    model = StatisticalArticlePage
    choose_one_text = "Choose Article page"
    choose_another_text = "Choose another Article page"
    edit_item_text = "Edit Article page"


class HighlightedMethodologyPageChooserViewSet(BaseHighlightedChildrenViewSet):
    model = MethodologyPage
    choose_one_text = "Choose Methodology page"
    choose_another_text = "Choose another Methodology page"
    edit_item_text = "Edit Methodology page"


featured_series_page_chooser_viewset = FeaturedSeriesPageChooserViewSet("topic_featured_series_page_chooser")
FeaturedSeriesPageChooserWidget = featured_series_page_chooser_viewset.widget_class

highlighted_article_page_chooser_viewset = HighlightedArticlePageChooserViewSet(
    "topic_highlighted_article_page_chooser"
)
HighlightedArticlePageChooserWidget = highlighted_article_page_chooser_viewset.widget_class

highlighted_methodology_page_chooser_viewset = HighlightedMethodologyPageChooserViewSet(
    "topic_highlighted_methodology_page_chooser"
)
HighlightedMethodologyPageChooserWidget = highlighted_methodology_page_chooser_viewset.widget_class


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
