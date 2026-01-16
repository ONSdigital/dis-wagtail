from typing import TYPE_CHECKING

from wagtail.admin.ui.tables import Column, DateColumn, LocaleColumn
from wagtail.admin.ui.tables.pages import PageStatusColumn
from wagtail.admin.views.generic.chooser import ChooseResultsView, ChooseView
from wagtail.admin.viewsets.chooser import ChooserViewSet

from cms.articles.models import ArticleSeriesPage
from cms.core.forms import NoLocaleFilterInChoosersForm

if TYPE_CHECKING:
    from wagtail.query import PageQuerySet


__all__ = [
    "FeaturedSeriesPageChooserViewSet",
    "FeaturedSeriesPageChooserWidget",
    "featured_series_page_chooser_viewset",
]


class FeaturedSeriesPageChooseViewMixin:
    model_class: ArticleSeriesPage
    filter_form_class = NoLocaleFilterInChoosersForm

    def get_object_list(self) -> PageQuerySet[ArticleSeriesPage]:
        return ArticleSeriesPage.objects.all().order_by("path")

    @property
    def columns(self) -> list[Column]:
        return [
            self.title_column,  # type: ignore[attr-defined]
            Column("parent", label="Topic", accessor="get_parent"),
            LocaleColumn(classname="w-text-16 w-w-[120px]"),  # w-w-[120px] is used to adjust the width
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


featured_series_page_chooser_viewset = FeaturedSeriesPageChooserViewSet("topic_featured_series_page_chooser")
FeaturedSeriesPageChooserWidget = featured_series_page_chooser_viewset.widget_class
