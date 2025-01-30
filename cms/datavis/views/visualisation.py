from collections.abc import Sequence
from typing import TYPE_CHECKING, Any, Optional

from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.generic.edit import BaseFormView
from wagtail.admin.ui.components import MediaContainer
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
    IndexView,
)

from cms.datavis.forms.visualisation import (
    VisualisationCopyForm,
    VisualisationTypeSelectForm,
)
from cms.datavis.models import Visualisation

from .mixins import RemoveChecksSidePanelMixin, RemoveSnippetIndexBreadcrumbItemMixin
from .specific import SpecificCreateView, SpecificDeleteView, SpecificEditView, SpecificHistoryView

if TYPE_CHECKING:
    from django.db.models import QuerySet
    from django.forms import Form
    from django.http import HttpResponse
    from django.utils.functional import Promise
    from wagtail.admin.panels import Panel
    from wagtail.admin.ui.action_menu import ActionMenu


class VisualisationIndexView(RemoveSnippetIndexBreadcrumbItemMixin, IndexView):
    def get_base_queryset(self) -> "QuerySet[Visualisation]":
        """Overrides the default implementation to fetch creating users in the
        same query (avoiding n+1 queries).
        """
        return self.model.objects.select_related("created_by")  # type: ignore[no-any-return]


class VisualisationTypeSelectView(
    RemoveSnippetIndexBreadcrumbItemMixin, LocaleMixin, PermissionCheckedMixin, WagtailAdminTemplateMixin, BaseFormView
):
    def get_breadcrumbs_items(self) -> Sequence[dict[str, "str | Promise"]]:
        return [
            *super().get_breadcrumbs_items(),
            {
                "label": _("Visualisations"),
                "url": reverse("wagtailsnippets_datavis_visualisation:list"),
            },
        ]

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
        specific_type = self.form.cleaned_data["specific_type"]
        return reverse(
            "wagtailsnippets_datavis_visualisation:specific_add",
            kwargs={"specific_type": specific_type},
        )


class VisualisationCreateView(RemoveChecksSidePanelMixin, RemoveSnippetIndexBreadcrumbItemMixin, SpecificCreateView):
    pass


class VisualisationDeleteView(RemoveSnippetIndexBreadcrumbItemMixin, SpecificDeleteView):
    pass


class VisualisationEditView(RemoveChecksSidePanelMixin, RemoveSnippetIndexBreadcrumbItemMixin, SpecificEditView):
    pass


class VisualisationHistoryView(RemoveSnippetIndexBreadcrumbItemMixin, SpecificHistoryView):
    pass


class VisualisationCopyView(RemoveChecksSidePanelMixin, RemoveSnippetIndexBreadcrumbItemMixin, SpecificEditView):
    action = "copy"
    permission_required = "add"
    success_message = _("%(model_name)s '%(object)s' created successfully.")

    def get_header_title(self) -> str:
        return f"Copy chart: {self.object}"

    def get_page_subtitle(self) -> str:
        return f"Copy: {self.object}"

    def get_bound_panel(self, *args: Any, **kwargs: Any) -> Optional["Panel"]:
        """Overrides EditView.get_bound_panel() to prevent the edit_handler from
        the viewset being used to generate the form class, because we have a
        specific form with specific fields we want to display.
        """
        return None

    def get_form(self, *args: Any, **kwargs: Any) -> "Form":
        form: Form = VisualisationCopyForm(
            data=self.request.POST or None,
            instance=self.object,
            for_user=self.request.user,
            initial={"name": self.object.name + " copy"},
        )
        return form

    def run_before_hook(self) -> None:
        """Overrides EditView.run_before_hook() to prevent irrelevant
        'before_edit_snippet' hook logic from running (this isn't an edit).
        """
        return None

    def run_after_hook(self) -> None:
        """Overrides EditView.run_after_hook() to prevent irrelevant
        'after_edit_snippet' hook logic from running (this isn't an edit).
        """
        return None

    def get_side_panels(self) -> "MediaContainer":
        """Overrides EditView.get_side_panels() to prevent any side panels
        from being displayed.
        """
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
        context: dict[str, Any] = super().get_context_data(**kwargs)
        context["action_url"] = self.request.path
        return context

    def save_instance(self) -> "Visualisation":
        """Called after the form is successfully validated - saves the object to the db
        and returns the new object. Override this to implement custom save logic.
        """
        instance: Visualisation = self.form.save()

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
