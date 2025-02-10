from typing import TYPE_CHECKING, ClassVar

from django.utils.translation import gettext_lazy as _
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


class FeaturedSeriesPageMixin:
    model_class: ArticleSeriesPage

    def get_object_list(self) -> "PageQuerySet[ArticleSeriesPage]":
        return ArticleSeriesPage.objects.all().order_by("path")

    @property
    def columns(self) -> list["Column"]:
        return [
            self.title_column,  # type: ignore[attr-defined]
            Column("parent", label=_("Topic"), accessor="get_parent"),
            DateColumn(
                "updated",
                label=_("Updated"),
                width="12%",
                accessor="latest_revision_created_at",
            ),
            PageStatusColumn("status", label=_("Status"), width="12%"),
        ]


class FeaturedSeriesPageChooseView(FeaturedSeriesPageMixin, ChooseView): ...


class FeaturedSeriesPageChooseResultsView(FeaturedSeriesPageMixin, ChooseResultsView): ...


class FeaturedSeriesPageChooserViewSet(ChooserViewSet):
    model = ArticleSeriesPage
    choose_view_class = FeaturedSeriesPageChooseView
    choose_results_view_class = FeaturedSeriesPageChooseResultsView
    register_widget = False
    choose_one_text = _("Choose Article Series page")
    choose_another_text = _("Choose another Article Series page")
    edit_item_text = _("Edit Article Series page")


class HighlightedChildPageMixin:
    def get_object_list(self) -> "PageQuerySet[StatisticalArticlePage | MethodologyPage]":
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
                label=_("Release date"),
                width="12%",
                accessor="release_date",
            ),
            PageStatusColumn("status", label=_("Status"), width="12%"),
        ]


class HighlightedPagePageChooseView(HighlightedChildPageMixin, ChooseView): ...


class HighlightedPagePageChooseResultsView(HighlightedChildPageMixin, ChooseResultsView): ...


class BaseHighlightedChildrenViewSet(ChooserViewSet):
    choose_view_class = HighlightedPagePageChooseView
    choose_results_view_class = HighlightedPagePageChooseResultsView
    register_widget = False
    preserve_url_parameters: ClassVar[list[str]] = ["multiple", "topic_page_id"]
    icon = "doc-empty-inverse"


class HighlightedArticlePageChooserViewSet(BaseHighlightedChildrenViewSet):
    model = StatisticalArticlePage
    choose_one_text = _("Choose Article page")
    choose_another_text = _("Choose another Article page")
    edit_item_text = _("Edit Article page")


class HighlightedMethodologyPageChooserViewSet(BaseHighlightedChildrenViewSet):
    model = MethodologyPage
    choose_one_text = _("Choose Methodology page")
    choose_another_text = _("Choose another Methodology page")
    edit_item_text = _("Edit Methodology page")


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
