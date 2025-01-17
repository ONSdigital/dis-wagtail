from collections.abc import Sequence
from typing import TYPE_CHECKING, Any, ClassVar, Optional

from django.urls import path, reverse
from django.utils.translation import gettext_lazy as _
from django.views.generic.edit import BaseFormView
from wagtail.admin.panels import FieldPanel, ObjectList
from wagtail.admin.ui.components import MediaContainer
from wagtail.admin.ui.side_panels import ChecksSidePanel
from wagtail.admin.views.generic.base import WagtailAdminTemplateMixin
from wagtail.admin.views.generic.mixins import LocaleMixin
from wagtail.admin.views.generic.permissions import PermissionCheckedMixin
from wagtail.log_actions import log
from wagtail.snippets.action_menu import (
    DeleteMenuItem,
    PublishMenuItem,
    UnpublishMenuItem,
)
from wagtail.snippets.views.snippets import (
    CreateView,
    DeleteView,
    EditView,
    HistoryView,
    IndexView,
    PreviewOnCreateView,
    PreviewOnEditView,
    SnippetViewSet,
    SnippetViewSetGroup,
)

from cms.datavis.admin.filters import DataSourceFilterSet, VisualisationFilterSet
from cms.datavis.admin.forms import DataSourceEditForm, VisualisationCopyForm, VisualisationEditForm, VisualisationTypeSelectForm
from cms.datavis.models import DataSource, Visualisation
from cms.datavis.utils import get_visualisation_type_model_from_name

if TYPE_CHECKING:
    from django.db.models import QuerySet
    from django.forms import Form
    from django.http import HttpRequest, HttpResponse
    from wagtail.admin.panels import EditHandler
    from wagtail.admin.ui.action_menu import ActionMenu
    from wagtail.snippets.views.snippets import SnippetViewSet


class VisualisationIndexView(IndexView):
    def get_base_queryset(self) -> "QuerySet[Visualisation]":
        return self.model.objects.select_related("created_by")


class VisualisationTypeSelectView(LocaleMixin, PermissionCheckedMixin, WagtailAdminTemplateMixin, BaseFormView):
    def get_form_class(self) -> type["Form"]:
        """Return the form class to use."""
        return VisualisationTypeSelectForm

    def get_template_names(self) -> list[str]:
        return ["datavis/admin/visualisation_type_select.html"]

    def form_valid(self, form: "Form") -> "HttpResponse":
        """Process the valid form data."""
        self.form = form  # pylint: disable=attribute-defined-outside-init
        return super().form_valid(form)

    def get_success_url(self) -> str:
        """Return the URL to redirect to after processing a valid form."""
        vis_type = self.form.cleaned_data["vis_type"]
        return reverse(
            "wagtailsnippets_datavis_visualisation:specific_add",
            kwargs={"vis_type": vis_type},
        )


class VisualisationTypeKwargMixin:
    def setup(self, request: "HttpRequest", *args: Any, **kwargs: Any) -> None:
        self.model = get_visualisation_type_model_from_name(kwargs["vis_type"])
        super().setup(request, *args, **kwargs)

    def get_panel(self) -> "EditHandler":
        edit_handler = self.model.edit_handler
        return edit_handler.bind_to_model(self.model)


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
        self.pk = kwargs.get("pk")

        # Fetch the specific object and use the specific type to set
        # self.model - allowing forms to be generated correctly. Our overrides
        # to `get_object()` should rule out repeat queries when the superclass
        # implementation calls `get_object()` again.
        self.object = self.get_object()
        self.model = type(self.object)

        super().setup(request, *args, **kwargs)

    def get_object(self, queryset: "QuerySet[Visualisation] | None" = None) -> "Visualisation":
        """Overrides the default implementation to return the specific object.
        Because views often make their own requests to `get_object()` in
        `setup()`, there is some caching in place to avoid repeat queries.
        """
        if getattr(self, "object", None):
            return self.object.specific
        try:
            return super().get_object(queryset).specific
        except TypeError:
            return super().get_object().specific

    def get_panel(self) -> "EditHandler":
        edit_handler = self.model.edit_handler
        return edit_handler.bind_to_model(self.model)


class SpecificAddView(VisualisationTypeKwargMixin, CreateView):
    def get_add_url(self) -> str:
        # This override is required so that the form posts back to this view
        return reverse(
            "wagtailsnippets_datavis_visualisation:specific_add",
            kwargs={"vis_type": self.kwargs["vis_type"]},
        )

    def get_preview_url(self) -> str:
        """Overrides the default implementation to include the chart-type
        in the preview URL, allowing it to identify the specific model.
        """
        args = [self.model._meta.label_lower]
        return reverse(self.preview_url_name, args=args)

    def get_side_panels(self) -> "MediaContainer":
        return MediaContainer([panel for panel in super().get_side_panels() if not isinstance(panel, ChecksSidePanel)])


class SpecificEditView(SpecificObjectViewMixin, EditView):
    action = "edit"

    def get_preview_url(self) -> str:
        """Overrides the default implementation to pass include the chart-type
        in the preview URL, allowing it to identify the specific model.
        """
        args = [self.model._meta.label_lower, self.object.pk]
        return reverse(self.preview_url_name, args=args)

    def get_side_panels(self) -> "MediaContainer":
        return MediaContainer([panel for panel in super().get_side_panels() if not isinstance(panel, ChecksSidePanel)])


class VisualisationCopyView(SpecificObjectViewMixin, EditView):
    action = "copy"
    permission_required = "add"
    success_message = _("%(model_name)s '%(object)s' created successfully.")

    def get_bound_panel(self, *args: Any, **kwargs: Any) -> Optional["EditHandler"]:
        return None

    def get_header_title(self) -> str:
        return f"Copy chart: {self.object}"

    def get_page_subtitle(self) -> str:
        return f"Copy: {self.object}"

    def get_form(self, *args: Any, **kwargs: Any) -> "Form":
        return VisualisationCopyForm(
            data=self.request.POST or None,
            instance=self.object,
            for_user=self.request.user,
            initial={"name": self.object.name + " copy"},
        )

    def run_before_hook(self) -> None:
        return self.run_hook("before_create_snippet", self.request, self.object)

    def run_after_hook(self) -> None:
        return self.run_hook("after_create_snippet", self.request, self.object)

    def get_side_panels(self) -> "MediaContainer":
        return MediaContainer()

    def _get_action_menu(self) -> "ActionMenu":
        menu = super()._get_action_menu()
        menu.menu_items = [
            item
            for item in menu.menu_items
            if not isinstance(item, DeleteMenuItem | PublishMenuItem | UnpublishMenuItem)
        ]
        return menu

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context["action_url"] = self.request.path
        return context

    def save_instance(self) -> "Visualisation":
        """Called after the form is successfully validated - saves the object to the db
        and returns the new object. Override this to implement custom save logic.
        """
        instance = self.form.save()

        log(
            instance=instance,
            action="wagtail.create",
            user=self.request.user,
            revision=None,
            content_changed=False,
        )

        return instance

    def get_success_url(self) -> str:
        return reverse(self.index_url_name)


class SpecificDeleteView(SpecificObjectViewMixin, DeleteView):
    def get_form(self, *args: Any, **kwargs: Any) -> "Form":
        """Overrides the default implementation to ensure 'instance' is set on
        the form. It's unclear why Wagtail doesn't do this by default, but
        `self.get_bound_panel()` raises an AttributeError without this.
        """
        form = super().get_form(*args, **kwargs)
        form.instance = self.object
        return form


class SpecificPreviewOnCreateView(VisualisationTypeKwargMixin, PreviewOnCreateView):
    pass


class SpecificPreviewOnEditView(VisualisationTypeKwargMixin, PreviewOnEditView):
    pass


class SpecificHistoryView(SpecificObjectViewMixin, HistoryView):
    pass


class VisualisationViewSet(SnippetViewSet):
    base_form_class = VisualisationEditForm
    index_view_class = VisualisationIndexView
    add_view_class = VisualisationTypeSelectView
    copy_view_class = VisualisationCopyView
    delete_view_class = SpecificDeleteView
    edit_view_class = SpecificEditView
    history_view_class = SpecificHistoryView
    model = Visualisation
    preview_on_add_view_class = SpecificPreviewOnCreateView
    preview_on_edit_view_class = SpecificPreviewOnEditView
    specific_add_view_class = SpecificAddView
    filterset_class = VisualisationFilterSet
    list_display: ClassVar[Sequence[str]] = [
        "name",
        "type_label",
        "created_by",
        "created_at",
        "last_updated_at",
    ]

    @property
    def specific_add_view(self) -> "SpecificAddView":
        return self.construct_view(self.specific_add_view_class, **self.get_add_view_kwargs())

    def get_urlpatterns(self) -> list[path]:
        urlpatterns = [
            pattern
            for pattern in super().get_urlpatterns()
            if getattr(pattern, "name", "") not in ["preview_on_add", "preview_on_edit"]
        ]
        urlpatterns.extend(
            [
                path("new/<str:vis_type>/", self.specific_add_view, name="specific_add"),
                path(
                    "preview/<str:vis_type>/",
                    self.preview_on_add_view,
                    name="preview_on_add",
                ),
                path(
                    "preview/<str:vis_type>/<str:pk>/",
                    self.preview_on_edit_view,
                    name="preview_on_edit",
                ),
            ]
        )
        return urlpatterns

    def get_add_view_kwargs(self, **kwargs: Any) -> dict[str, Any]:
        kwargs = super().get_add_view_kwargs(**kwargs)
        del kwargs["panel"]
        del kwargs["form_class"]
        return kwargs

    def get_edit_view_kwargs(self, **kwargs: Any) -> dict[str, Any]:
        kwargs = super().get_edit_view_kwargs(**kwargs)
        del kwargs["panel"]
        del kwargs["form_class"]
        return kwargs

    @property
    def preview_on_add_view(self) -> "PreviewOnCreateView":
        return self.construct_view(self.preview_on_add_view_class)

    @property
    def preview_on_edit_view(self) -> "PreviewOnEditView":
        return self.construct_view(self.preview_on_edit_view_class)


class DataSourceViewSet(SnippetViewSet):
    model = DataSource
    base_form_class = DataSourceEditForm
    list_display: ClassVar[Sequence[str]] = ["title", "column_count", "created_by", "created_at", "last_updated_at"]
    list_select_related: ClassVar[Sequence[str]] = ["created_by"]
    filterset_class = DataSourceFilterSet

    edit_handler = ObjectList(
        [
            FieldPanel("title"),
            FieldPanel("collection"),
            FieldPanel("csv_file"),
            FieldPanel("table"),
        ],
        base_form_class=DataSourceEditForm,
    )


class DataVisViewSetGroup(SnippetViewSetGroup):
    menu_label = "Datavis"
    icon = "fa-chart-line"
    items: ClassVar[Sequence[type["SnippetViewSet"]]] = [DataSourceViewSet, VisualisationViewSet]
