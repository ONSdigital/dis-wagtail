from typing import TYPE_CHECKING, Any, Union

from django.urls import reverse
from django.utils.html import format_html
from wagtail.admin.panels import FieldPanel, HelpPanel

from cms.bundles.permissions import user_can_manage_bundles
from cms.bundles.utils import get_page_title_with_workflow_status
from cms.bundles.viewsets.bundle_page_chooser import PagesWithDraftsForBundleChooserWidget

if TYPE_CHECKING:
    from django.db.models import Model
    from django.utils.safestring import SafeString
    from wagtail.models import Page


class BundleStatusPanel(HelpPanel):
    class BoundPanel(HelpPanel.BoundPanel):
        def __init__(self, **kwargs: Any) -> None:
            super().__init__(**kwargs)
            self.content = self._content_for_instance(self.instance)

        def _content_for_instance(self, instance: "Model") -> Union[str, "SafeString"]:
            if not hasattr(instance, "status"):
                return ""

            return format_html("<p>{}</p>", instance.get_status_display())  # type: ignore[attr-defined]


class BundleNotePanel(HelpPanel):
    """An extended HelpPanel class."""

    class BoundPanel(HelpPanel.BoundPanel):
        def __init__(self, **kwargs: Any) -> None:
            super().__init__(**kwargs)
            self.content = self._content_for_instance(self.instance)

        def _content_for_instance(self, instance: "Model") -> Union[str, "SafeString"]:
            if not hasattr(instance, "active_bundle"):
                return ""

            can_manage = user_can_manage_bundles(self.request.user)
            if bundle := instance.active_bundle:
                if can_manage:
                    return format_html(
                        "<p>This page is in the following bundle: "
                        '<a href="{}" target="_blank" title="Manage bundle">{}</a> (Status: {})</p>',
                        reverse("bundle:edit", args=[bundle.pk]),
                        bundle.name,
                        bundle.get_status_display(),
                    )
                return format_html(
                    "<p>This page is in the following bundle: {} (Status: {})</p>",
                    bundle.name,
                    bundle.get_status_display(),
                )

            if can_manage:
                return format_html(
                    "<p>This page is not part of any bundles. "
                    '<a href="{}" class="button button-small button-secondary">Add to Bundle</a></p>',
                    reverse("bundles:add_to_bundle", args=(instance.pk,), query={"next": self.request.path}),
                )
            return format_html("<p>{}</p>", "This page is not part of any bundles.")


class CustomAdminPageChooser(PagesWithDraftsForBundleChooserWidget):
    def get_display_title(self, instance: "Page") -> str:
        return get_page_title_with_workflow_status(instance)


class PageChooserWithStatusPanel(FieldPanel):
    """A custom page chooser panel that includes the page workflow status."""

    def get_form_options(self) -> dict[str, list | dict]:
        opts: dict[str, list | dict] = super().get_form_options()

        widgets = opts.setdefault("widgets", {})
        widgets[self.field_name] = CustomAdminPageChooser()

        return opts

    class BoundPanel(FieldPanel.BoundPanel):
        def __init__(self, **kwargs: Any) -> None:
            """Sets the panel heading to the page verbose name to help differentiate page types."""
            super().__init__(**kwargs)
            if page := self.instance.page:
                self.heading = page.specific_deferred.get_verbose_name()
