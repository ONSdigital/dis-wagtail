from typing import TYPE_CHECKING, Any, Optional

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

if TYPE_CHECKING:
    from django.forms import Form
    from wagtail.admin.panels import Panel
    from wagtail.models import SpecificMixin


class SpecificModelFromObjectMixin:
    object: "SpecificMixin"

    def get_object(self, *args: Any, **kwargs: Any) -> "SpecificMixin":
        """Overrides the default implementation to return the specific object.
        Because views often make their own requests to `get_object()` in
        `setup()`, there is some caching in place to avoid repeat queries.
        """
        if getattr(self, "object", None):
            return self.object
        return super().get_object(*args, **kwargs).specific  # type: ignore[misc]

    @cached_property
    def specific_model(self) -> type["SpecificMixin"]:
        return self.get_object().specific_class  # type: ignore[no-any-return]


class SpecificModelFromURLKwargMixin:
    """A mixin for views that use a 'specific_type' URL kwarg to
    determine the specific model class.
    """

    model: type["SpecificMixin"]
    kwargs: dict[str, Any]

    @cached_property
    def specific_model(self) -> type["SpecificMixin"]:
        return get_child_model_from_name(self.model, self.kwargs["specific_type"])


class SpecificModelFormMixin:
    """A mixin for views that should use the edit_handler defined on the
    specific model class to generate an edit form.
    """

    model: type["SpecificMixin"]
    form_class: Optional[type["Form"]]
    specific_model: type["SpecificMixin"]

    def get_panel(self) -> "Panel":
        panel = self.specific_model.edit_handler
        return panel.bind_to_model(self.specific_model)

    def get_form_class(self) -> type["Form"]:
        self.panel = self.get_panel()
        if self.form_class:
            return self.form_class
        return self.panel.get_form_class()  # type: ignore[no-any-return]


class SpecificCreateView(
    SpecificModelFormMixin,
    SpecificModelFromURLKwargMixin,
    CreateView,
):
    def get_object(self, *args: Any, **kwargs: Any) -> "SpecificMixin":
        return self.specific_model()

    def get_page_subtitle(self) -> str:
        return capfirst(self.specific_model._meta.verbose_name)  # type: ignore[no-any-return]

    @cached_property
    def specific_add_url_name(self) -> str:
        meta = self.model._meta
        return f"wagtailsnippets_{meta.app_label}_{meta.model_name}:specific_add"

    def get_add_url(self) -> str:
        # This override is required so that the form posts back to this view
        return reverse(
            self.specific_add_url_name,
            kwargs={"specific_type": self.kwargs["specific_type"]},
        )

    def get_preview_url(self) -> str:
        """Overrides the default implementation to include the chart-type
        in the preview URL, allowing it to identify the specific model.
        """
        args = [self.specific_model._meta.label_lower]
        return reverse(self.preview_url_name, args=args)


class SpecificEditView(
    SpecificModelFormMixin,
    SpecificModelFromObjectMixin,
    EditView,
):
    def get_preview_url(self) -> str:
        """Overrides the default implementation to pass include the chart-type
        in the preview URL, allowing it to identify the specific model.
        """
        args = [self.specific_model._meta.label_lower, self.object.pk]
        return reverse(self.preview_url_name, args=args)


class SpecificDeleteView(SpecificModelFromObjectMixin, DeleteView):
    pass


class SpecificPreviewOnCreateView(SpecificModelFormMixin, SpecificModelFromURLKwargMixin, PreviewOnCreateView):
    def get_object(self, *args: Any, **kwargs: Any) -> "SpecificMixin":
        return self.specific_model()


class SpecificPreviewOnEditView(SpecificModelFormMixin, SpecificModelFromObjectMixin, PreviewOnEditView):
    pass


class SpecificHistoryView(SpecificModelFromObjectMixin, HistoryView):
    pass
