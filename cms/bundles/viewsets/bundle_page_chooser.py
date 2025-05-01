from typing import TYPE_CHECKING, ClassVar

from wagtail.admin.ui.tables import Column, DateColumn
from wagtail.admin.ui.tables.pages import PageStatusColumn
from wagtail.admin.views.generic.chooser import ChooseResultsView, ChooseView
from wagtail.admin.viewsets.chooser import ChooserViewSet
from wagtail.admin.widgets import BaseChooser
from wagtail.models import Page

from cms.bundles.utils import get_bundleable_page_types, get_pages_in_active_bundles

if TYPE_CHECKING:
    from wagtail.query import PageQuerySet


class PagesWithDraftsMixin:
    results_template_name = "bundles/bundle_page_chooser_results.html"

    def get_object_list(self) -> "PageQuerySet":
        """Limits the pages that can be chosen for a bundle.

        Pages are included if they
        - are a BundledPageMixin subclass
        - have unpublished changes
        - are not in another active bundle
        """
        return (
            Page.objects.specific(defer=True)
            # using pk_in because the direct has_unpublished_changes=True filter
            # requires Page to have has_unpublished_changes added to search fields which we cannot do
            .filter(pk__in=Page.objects.type(*get_bundleable_page_types()).filter(has_unpublished_changes=True))
            .exclude(pk__in=get_pages_in_active_bundles())
            .order_by("-latest_revision_created_at")
        )

    @property
    def columns(self) -> list["Column"]:
        title_column = self.title_column  # type: ignore[attr-defined]
        title_column.accessor = "get_admin_display_title"

        return [
            title_column,
            Column("parent", label="Parent", accessor="get_parent"),
            Column("locale", label="Locale"),
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
    preserve_url_parameters: ClassVar[list[str]] = ["multiple", "bundle_id"]
    register_widget = False

    icon = "doc-empty-inverse"
    choose_one_text = "Choose a page"
    choose_another_text = "Choose another page"
    edit_item_text = "Edit this page"


bundle_page_chooser_viewset = PagesWithDraftsForBundleChooserViewSet("bundle_page_chooser")
PagesWithDraftsForBundleChooserWidget: type[BaseChooser] = bundle_page_chooser_viewset.widget_class
