from typing import TYPE_CHECKING

from django.utils.translation import gettext_lazy as _
from wagtail.admin.ui.tables import Column, DateColumn
from wagtail.admin.ui.tables.pages import PageStatusColumn
from wagtail.admin.views.generic.chooser import ChooseResultsView, ChooseView
from wagtail.admin.viewsets.chooser import ChooserViewSet

from cms.articles.models import ArticleSeriesPage

if TYPE_CHECKING:
    from wagtail.query import PageQuerySet


__all__ = [
    "FeaturedSeriesPageChooserViewSet",
    "FeaturedSeriesPageChooserWidget",
    "featured_series_page_chooser_viewset",
]


class FeaturedSeriesPageChooseViewMixin:
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


class FeaturedSeriesPageChooseView(FeaturedSeriesPageChooseViewMixin, ChooseView): ...


class FeaturedSeriesPageChooseResultsView(FeaturedSeriesPageChooseViewMixin, ChooseResultsView): ...


class FeaturedSeriesPageChooserViewSet(ChooserViewSet):
    model = ArticleSeriesPage
    choose_view_class = FeaturedSeriesPageChooseView
    choose_results_view_class = FeaturedSeriesPageChooseResultsView
    register_widget = False
    choose_one_text = _("Choose Article Series page")
    choose_another_text = _("Choose another Article Series page")
    edit_item_text = _("Edit Article Series page")


featured_series_page_chooser_viewset = FeaturedSeriesPageChooserViewSet("topic_featured_series_page_chooser")
FeaturedSeriesPageChooserWidget = featured_series_page_chooser_viewset.widget_class
