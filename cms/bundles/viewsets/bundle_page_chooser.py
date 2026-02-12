from typing import TYPE_CHECKING, Any, ClassVar

from django import forms
from wagtail.admin.forms.choosers import BaseFilterForm, LocaleFilterMixin, SearchFilterMixin
from wagtail.admin.ui.tables import Column, DateColumn, LocaleColumn
from wagtail.admin.ui.tables.pages import PageStatusColumn
from wagtail.admin.views.generic.chooser import ChooseResultsView, ChooseView, ChosenMultipleView, ChosenView
from wagtail.admin.viewsets.chooser import ChooserViewSet
from wagtail.admin.widgets import BaseChooser
from wagtail.models import Page

from cms.bundles.utils import (
    get_bundleable_page_types,
    get_page_title_with_workflow_status,
    get_pages_in_active_bundles,
)

if TYPE_CHECKING:
    from wagtail.query import PageQuerySet


class PagesWithDraftsMixinFilterForm(LocaleFilterMixin, SearchFilterMixin, BaseFilterForm):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._page_type_map = {model.__name__: model for model in get_bundleable_page_types()}
        choices = [(model_name, model.get_verbose_name()) for model_name, model in self._page_type_map.items()]
        self.fields["page_type"] = forms.ChoiceField(
            choices=[("", "All"), *choices],
            required=False,
            widget=forms.Select(attrs={"data-chooser-modal-search-filter": True}),
        )

    def filter(self, objects: PageQuerySet) -> PageQuerySet:
        selected_page_type = self.cleaned_data.get("page_type")
        if selected_page_type:
            objects = objects.type(self._page_type_map[selected_page_type])
        return super().filter(objects)


class PagesWithDraftsMixin:
    results_template_name = "bundles/bundle_page_chooser_results.html"
    filter_form_class = PagesWithDraftsMixinFilterForm

    def get_object_list(self) -> PageQuerySet:
        """Limits the pages that can be chosen for a bundle.

        Pages are included if they
        - are a BundledPageMixin subclass
        - have unpublished changes
        - are not in another active bundle
        """
        pre_filter_q = Page.objects.type(*get_bundleable_page_types()).filter(
            has_unpublished_changes=True,
            alias_of__isnull=True,  # not an alias
            go_live_at__isnull=True,  # scheduled go-live draft
            expire_at__isnull=True,  # scheduled expiry draft
            latest_revision__content__go_live_at=None,  # live + scheduled go-live draft
            latest_revision__content__expire_at=None,  # live + scheduled expiry draft
        )

        return (
            Page.objects.specific(defer=True)
            # using pk_in because the direct has_unpublished_changes and alias_of filter
            # requires Page to have them added to search fields which we cannot do
            .filter(pk__in=pre_filter_q)
            .exclude(pk__in=get_pages_in_active_bundles())
            .order_by("-latest_revision_created_at")
        )

    @property
    def columns(self) -> list[Column]:
        title_column = self.title_column  # type: ignore[attr-defined]
        title_column.accessor = "get_admin_display_title"

        return [
            title_column,
            Column("parent", label="Parent", accessor=lambda p: getattr(p, "parent_for_choosers", p.get_parent())),
            LocaleColumn(classname="w-text-16 w-w-[120px]"),  # w-w-[120px] is used to adjust the width
            DateColumn(
                "updated",
                label="Updated",
                accessor="latest_revision_created_at",
            ),
            Column(
                "type",
                label="Type",
                accessor="page_type_display_name",
            ),
            PageStatusColumn("status", label="Status", width="12%"),
        ]


class PagesWithDraftsForBundleChooseView(PagesWithDraftsMixin, ChooseView): ...


class PagesWithDraftsForBundleChooseResultsView(PagesWithDraftsMixin, ChooseResultsView): ...


class BundlePagesChosenMixin:
    def get_display_title(self, instance: Page) -> str:
        return get_page_title_with_workflow_status(instance)


class BundlePagesChosenView(BundlePagesChosenMixin, ChosenView): ...


class BundlePagesChosenMultipleView(BundlePagesChosenMixin, ChosenMultipleView): ...


class PagesWithDraftsForBundleChooserViewSet(ChooserViewSet):
    model = Page
    choose_view_class = PagesWithDraftsForBundleChooseView
    choose_results_view_class = PagesWithDraftsForBundleChooseResultsView
    chosen_view_class = BundlePagesChosenView
    chosen_multiple_view_class = BundlePagesChosenMultipleView
    preserve_url_parameters: ClassVar[list[str]] = ["multiple", "bundle_id"]
    register_widget = False

    icon = "doc-empty-inverse"
    choose_one_text = "Choose a page"
    choose_another_text = "Choose another page"
    edit_item_text = "Edit this page"


bundle_page_chooser_viewset = PagesWithDraftsForBundleChooserViewSet("bundle_page_chooser")
PagesWithDraftsForBundleChooserWidget: type[BaseChooser] = bundle_page_chooser_viewset.widget_class
