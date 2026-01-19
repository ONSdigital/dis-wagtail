from typing import TYPE_CHECKING

from wagtail.admin.ui.tables import Column, UserColumn
from wagtail.admin.views.generic.chooser import ChooseResultsView, ChooseView
from wagtail.admin.viewsets.chooser import ChooserViewSet

from cms.bundles.models import Bundle

if TYPE_CHECKING:
    from cms.bundles.models import BundlesQuerySet


class BundleChooseViewMixin:
    icon = "boxes-stacked"

    @property
    def columns(self) -> list[Column]:
        """Defines the list of desired columns in the chooser."""
        return [
            *super().columns,  # type: ignore[misc]
            Column("scheduled_publication_date"),
            UserColumn("created_by"),
        ]

    def get_object_list(self) -> BundlesQuerySet:
        """Overrides the default object list to only fetch the fields we're using."""
        queryset: BundlesQuerySet = Bundle.objects.editable().select_related("created_by").only("name", "created_by")
        return queryset


class BundleChooseView(BundleChooseViewMixin, ChooseView): ...


class BundleChooseResultsView(BundleChooseViewMixin, ChooseResultsView): ...


class BundleChooserViewSet(ChooserViewSet):
    """Defines the chooser viewset for Bundles."""

    model = Bundle
    icon = "boxes-stacked"
    choose_view_class = BundleChooseView
    choose_results_view_class = BundleChooseResultsView


bundle_chooser_viewset = BundleChooserViewSet("bundle_chooser")

BundleChooserWidget = bundle_chooser_viewset.widget_class
