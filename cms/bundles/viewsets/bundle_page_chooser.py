from functools import cache
from typing import TYPE_CHECKING

from wagtail.admin.ui.tables import Column, DateColumn
from wagtail.admin.ui.tables.pages import PageStatusColumn
from wagtail.admin.views.generic.chooser import ChooseResultsView, ChooseView
from wagtail.admin.viewsets.chooser import ChooserViewSet
from wagtail.admin.widgets import BaseChooser
from wagtail.models import Page, get_page_models

if TYPE_CHECKING:
    from wagtail.query import PageQuerySet


@cache
def get_bundleable_page_types() -> list[type[Page]]:
    # imported inline to avoid partial-loaded module error
    from cms.bundles.models import BundledPageMixin  # pylint: disable=import-outside-toplevel

    return [model for model in get_page_models() if issubclass(model, BundledPageMixin)]


class PagesWithDraftsMixin:
    def get_object_list(self) -> "PageQuerySet":
        return (
            Page.objects.type(*get_bundleable_page_types())
            .specific(defer=True)
            .filter(has_unpublished_changes=True)
            .order_by("-latest_revision_created_at")
        )

    @property
    def columns(self) -> list["Column"]:
        title_column = self.title_column  # type: ignore[attr-defined]
        title_column.accessor = "get_admin_display_title"

        return [
            title_column,
            Column("parent", label="Parent", accessor="get_parent"),
            DateColumn(
                "updated",
                label="Updated",
                width="12%",
                accessor="latest_revision_created_at",
            ),
            Column(
                "type",
                label="Type",
                width="12%",
                accessor="page_type_display_name",
            ),
            PageStatusColumn("status", label="Status", width="12%"),
        ]


class PagesWithDraftsForBundleChooseView(PagesWithDraftsMixin, ChooseView): ...


class PagesWithDraftsForBundleChooseResultsView(PagesWithDraftsMixin, ChooseResultsView): ...


class PagesWithDraftsForBundleChooserViewSet(ChooserViewSet):
    model = Page
    choose_view_class = PagesWithDraftsForBundleChooseView
    choose_results_view_class = PagesWithDraftsForBundleChooseResultsView
    register_widget = False

    icon = "doc-empty-inverse"
    choose_one_text = "Choose a page"
    choose_another_text = "Choose another page"
    edit_item_text = "Edit this page"


bundle_page_chooser_viewset = PagesWithDraftsForBundleChooserViewSet("bundle_page_chooser")
PagesWithDraftsForBundleChooserWidget: type[BaseChooser] = bundle_page_chooser_viewset.widget_class
