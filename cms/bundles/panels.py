from typing import TYPE_CHECKING, Any, Union, cast
from urllib.parse import urlencode

from django.urls import reverse
from django.utils.html import format_html
from wagtail.admin.panels import FieldPanel, HelpPanel, MultipleChooserPanel

from cms.datasets.views import dataset_chooser_viewset
from cms.release_calendar.utils import get_release_calendar_page_details
from cms.release_calendar.viewsets import FutureReleaseCalendarChooserWidget

from .permissions import user_can_manage_bundles
from .utils import get_page_title_with_workflow_status
from .viewsets.bundle_page_chooser import PagesWithDraftsForBundleChooserWidget

if TYPE_CHECKING:
    from django.db.models import Model
    from django.utils.safestring import SafeString
    from wagtail.models import Page

    from cms.release_calendar.models import ReleaseCalendarPage


class BundleDatasetChooserWidget(dataset_chooser_viewset.widget_class):  # type: ignore[name-defined]
    """Custom dataset chooser widget that adds for_bundle=true parameter to the chooser URL."""

    def get_chooser_modal_url(self) -> str:
        """Override to add for_bundle=true query parameter."""
        base_url: str = super().get_chooser_modal_url()
        separator = "&" if "?" in base_url else "?"
        return f"{base_url}{separator}{urlencode({'for_bundle': 'true'})}"


class BundleStatusPanel(HelpPanel):
    class BoundPanel(HelpPanel.BoundPanel):
        def __init__(self, **kwargs: Any) -> None:
            super().__init__(**kwargs)
            self.content = self._content_for_instance(self.instance)

        def _content_for_instance(self, instance: Model) -> Union[str, SafeString]:
            if not hasattr(instance, "status"):
                return ""

            return format_html("<p>{}</p>", instance.get_status_display())  # type: ignore[attr-defined]


class BundleNotePanel(HelpPanel):
    """An extended HelpPanel class."""

    class BoundPanel(HelpPanel.BoundPanel):
        def __init__(self, **kwargs: Any) -> None:
            super().__init__(**kwargs)
            self.content = self._content_for_instance(self.instance)

        def _content_for_instance(self, instance: Model) -> Union[str, SafeString]:
            if not hasattr(instance, "active_bundle"):
                return ""

            can_manage = user_can_manage_bundles(self.request.user)

            if bundle := instance.active_bundle:
                html = "<p>This page is in the following bundle: {} (Status: {})</p>"
                if can_manage:
                    link = format_html(
                        '<a href="{}" target="_blank" title="Manage bundle">{}</a>',
                        reverse("bundle:edit", args=[bundle.pk]),
                        bundle.name,
                    )
                    return format_html(html, link, bundle.get_status_display())
                return format_html(html, bundle.name, bundle.get_status_display())

            if can_manage and instance.pk:
                return format_html(
                    "<p>This page is not part of any bundles. "
                    '<a href="{}" class="button button-small button-secondary">Add to Bundle</a></p>',
                    reverse("bundles:add_to_bundle", args=(instance.pk,), query={"next": self.request.path}),
                )
            return format_html("<p>{}</p>", "This page is not part of any bundles.")


class BundleFieldPanel(FieldPanel):
    """Defines a bundle-specific FieldPanel that is conditionally read-only."""

    def __init__(self, field_name: str, accessor: str | None = None, **kwargs: Any) -> None:
        super().__init__(field_name, **kwargs)
        self.accessor = accessor

    def clone_kwargs(self) -> dict[str, Any]:
        kwargs: dict[str, Any] = super().clone_kwargs()
        kwargs["accessor"] = self.accessor
        return kwargs

    class BoundPanel(FieldPanel.BoundPanel):
        def __init__(self, **kwargs: Any) -> None:
            super().__init__(**kwargs)

            if self.panel.accessor and getattr(self.instance, f"{self.panel.accessor}_id"):
                instance = getattr(self.instance, self.panel.accessor)
                self.read_only = getattr(instance, "is_ready_to_be_published", False)

    def format_value_for_display(self, value: Any) -> str:
        if value is None:
            return ""  # an empty string looks better than "None"
        return cast(str, super().format_value_for_display(value))


class BundleMultipleChooserPanel(MultipleChooserPanel):
    """Defines a bundle-specific MultiFieldPanel that is conditionally read-only."""

    def get_form_options(self) -> dict[str, Any]:
        """Override to inject custom widget for bundled_datasets."""
        opts: dict[str, Any] = super().get_form_options()

        # If this is the bundled_datasets panel, inject our custom widget
        if self.relation_name == "bundled_datasets":
            formset_opts = opts["formsets"][self.relation_name]
            widgets = formset_opts.setdefault("widgets", {})
            widgets[self.chooser_field_name] = BundleDatasetChooserWidget()

        return opts

    class BoundPanel(MultipleChooserPanel.BoundPanel):
        def __init__(self, **kwargs: Any) -> None:
            super().__init__(**kwargs)

            self.read_only = self.instance.is_ready_to_be_published

        def get_context_data(self, parent_context: dict[str, Any] | None = None) -> dict[str, Any]:
            context: dict[str, Any] = super().get_context_data(parent_context)
            if self.read_only:
                context["can_order"] = False
            return context


class CustomAdminPageChooser(PagesWithDraftsForBundleChooserWidget):
    def get_display_title(self, instance: Page) -> str:
        return get_page_title_with_workflow_status(instance)


class PageChooserWithStatusPanel(BundleFieldPanel):
    """A custom page chooser panel that includes the page workflow status."""

    def get_form_options(self) -> dict[str, list | dict]:
        opts: dict[str, list | dict] = super().get_form_options()

        widgets = opts.setdefault("widgets", {})
        widgets[self.field_name] = CustomAdminPageChooser()

        return opts

    def format_value_for_display(self, value: Any) -> str:
        if value is None:
            return ""
        return get_page_title_with_workflow_status(value)

    class BoundPanel(BundleFieldPanel.BoundPanel):
        def __init__(self, **kwargs: Any) -> None:
            """Sets the panel heading to the page verbose name to help differentiate page types."""
            super().__init__(**kwargs)
            if page := self.instance.page:
                self.heading = page.specific_deferred.get_verbose_name()


class CustomReleaseCalendarPageChooser(FutureReleaseCalendarChooserWidget):
    # Override BaseChooser's default get_display_title to return custom text display
    def get_display_title(self, instance: Page) -> str:
        return get_release_calendar_page_details(instance)


class ReleaseChooserWithDetailsPanel(BundleFieldPanel):
    """A custom page chooser panel that includes the release calendar page title, status and release date."""

    def get_form_options(self) -> dict[str, list | dict]:
        opts: dict[str, list | dict] = super().get_form_options()

        widgets = opts.setdefault("widgets", {})
        widgets[self.field_name] = CustomReleaseCalendarPageChooser()

        return opts

    def format_value_for_display(self, value: ReleaseCalendarPage | None) -> str:
        if value is None:
            return ""
        return get_release_calendar_page_details(value)
