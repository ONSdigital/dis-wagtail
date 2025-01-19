from collections.abc import Sequence
from typing import TYPE_CHECKING, Any

from django.contrib.admin.utils import unquote
from django.urls import reverse
from django.utils.functional import cached_property
from django.utils.text import capfirst
from wagtail.snippets.views.snippets import (
    CreateView,
    DeleteView,
    EditView,
    HistoryView,
    PreviewOnCreateView,
    PreviewOnEditView,
)

from cms.datavis.utils import get_child_model_from_name

from .mixins import RemoveChecksSidePanelMixin

if TYPE_CHECKING:
    from django.db.models import Model, QuerySet
    from django.forms import Form
    from django.http import HttpRequest
    from django.utils.functional import Promise
    from wagtail.admin.panels import Panel
    from wagtail.models import SpecificMixin


class ParentModelMixin:
    @cached_property
    def parent_model(self) -> type["SpecificMixin"]:
        parents: Sequence[Model] = self.model._meta.get_parent_list()  # type: ignore[attr-defined]
        if parents:
            return parents[-1]  # type: ignore[return-value]
        return self.model  # type: ignore[attr-defined,no-any-return]

    @cached_property
    def url_namespace(self) -> str:
        return f"wagtailsnippets_{self.parent_model._meta.label_lower}"


class SpecificTypeURLKwargMixin(ParentModelMixin):
    """A mixin for views that use a 'specific_type' URL kwarg to
    determine the specific model class.
    """

    def setup(self, request: "HttpRequest", *args: Any, **kwargs: Any) -> None:
        self.model = get_child_model_from_name(self.parent_model, kwargs["specific_type"])
        super().setup(request, *args, **kwargs)  # type: ignore[misc]


class CorrectIndexBreadcrumbMixin(ParentModelMixin):
    """A mixin for Visualisation views that include a breadcrumb
    item for the index view using the specific model name, but we
    want it to always read "Visualisation".
    """

    def get_breadcrumbs_items(self) -> Sequence[dict[str, "str | Promise"]]:
        items: list[dict[str, str | Promise]] = super().get_breadcrumbs_items()  # type: ignore[misc]
        for item in items:
            if item["url"] == reverse(self.index_url_name):  # type: ignore[attr-defined]
                item["label"] = capfirst(str(self.parent_model._meta.verbose_name_plural))
        return items


class SpecificModelPanelMixin:
    """A mixin for views that should use the edit_handler defined on the
    specific model class once it has been identified, instead of the one
    defined on the base class or viewset.
    """

    def get_panel(self) -> "Panel":
        panel = self.model.edit_handler  # type: ignore[attr-defined]
        return panel.bind_to_model(self.model)  # type: ignore[attr-defined]


class SpecificObjectViewMixin:
    draftstate_enabled = False
    locking_enabled = False
    preview_enabled = True
    revision_enabled = False

    def setup(self, request: "HttpRequest", *args: Any, **kwargs: Any) -> None:
        # NOTE: These 3 attributes will be reset by the superclass implementation,
        # but need to be set for the `get_object()` method to work
        # correctly
        self.request = request
        self.args = args
        self.kwargs = kwargs
        try:
            quoted_pk = self.kwargs[self.pk_url_kwarg]  # type: ignore[attr-defined]
        except KeyError:
            quoted_pk = self.args[0]
        self.pk = unquote(str(quoted_pk))

        # Fetch the specific object and use the specific type to set
        # self.model - allowing forms to be generated correctly. Our overrides
        # to `get_object()` should rule out repeat queries when the superclass
        # implementation calls `get_object()` again.
        self.object = self.get_object()
        self.model = type(self.object)

        super().setup(request, *args, **kwargs)  # type: ignore[misc]

    def get_object(self, queryset: "QuerySet | None" = None) -> "SpecificMixin":
        """Overrides the default implementation to return the specific object.
        Because views often make their own requests to `get_object()` in
        `setup()`, there is some caching in place to avoid repeat queries.
        """
        if getattr(self, "object", None):
            return self.object.specific
        try:
            # For views that support passing a queryset to get_object()
            return super().get_object(queryset).specific  # type: ignore[misc]
        except TypeError:
            # For all other views
            return super().get_object().specific  # type: ignore[misc]


class SpecificCreateView(
    CorrectIndexBreadcrumbMixin,
    RemoveChecksSidePanelMixin,
    SpecificModelPanelMixin,
    SpecificTypeURLKwargMixin,
    CreateView,
):
    def get_add_url(self) -> str:
        # This override is required so that the form posts back to this view
        return reverse(
            f"{self.url_namespace}:specific_add",
            kwargs={"specific_type": self.kwargs["specific_type"]},
        )

    def get_preview_url(self) -> str:
        """Overrides the default implementation to include the chart-type
        in the preview URL, allowing it to identify the specific model.
        """
        args = [self.model._meta.label_lower]
        return reverse(self.preview_url_name, args=args)


class SpecificEditView(
    CorrectIndexBreadcrumbMixin,
    RemoveChecksSidePanelMixin,
    SpecificModelPanelMixin,
    SpecificObjectViewMixin,
    EditView,
):
    def get_preview_url(self) -> str:
        """Overrides the default implementation to pass include the chart-type
        in the preview URL, allowing it to identify the specific model.
        """
        args = [self.model._meta.label_lower, self.object.pk]
        return reverse(self.preview_url_name, args=args)


class SpecificDeleteView(CorrectIndexBreadcrumbMixin, SpecificModelPanelMixin, SpecificObjectViewMixin, DeleteView):
    def get_form(self, *args: Any, **kwargs: Any) -> "Form":
        """Overrides the default implementation to ensure 'instance' is set on
        the form. It's unclear why Wagtail doesn't do this by default, but
        `self.get_bound_panel()` raises an AttributeError without this.
        """
        form: Form = super().get_form(*args, **kwargs)
        form.instance = self.object  # type: ignore[attr-defined]
        return form


class SpecificPreviewOnCreateView(SpecificModelPanelMixin, SpecificTypeURLKwargMixin, PreviewOnCreateView):
    pass


class SpecificPreviewOnEditView(SpecificModelPanelMixin, SpecificTypeURLKwargMixin, PreviewOnEditView):
    pass


class SpecificHistoryView(SpecificObjectViewMixin, HistoryView):
    pass
