from typing import TYPE_CHECKING, Any, Union

from django.urls import reverse
from django.utils.html import format_html
from wagtail.admin.panels import HelpPanel, PageChooserPanel

from cms.bundles.permissions import user_can_manage_bundles
from cms.bundles.viewsets.bundle_page_chooser import PagesWithDraftsForBundleChooserWidget

if TYPE_CHECKING:
    from django.db.models import Model
    from django.utils.safestring import SafeString
    from wagtail.models import Page


class BundleNotePanel(HelpPanel):
    """An extended HelpPanel class."""

    class BoundPanel(HelpPanel.BoundPanel):
        def __init__(self, **kwargs: Any) -> None:
            super().__init__(**kwargs)
            self.content = self._content_for_instance(self.instance)

        def _content_for_instance(self, instance: "Model") -> Union[str, "SafeString"]:
            if not hasattr(instance, "active_bundle"):
                return ""

            if bundle := instance.active_bundle:
                if user_can_manage_bundles(self.request.user):
                    content = format_html(
                        "<p>This page is in the following bundle: "
                        '<a href="{}" target="_blank" title="Manage bundle">{}</a> (Status: {})</p>',
                        reverse("bundle:edit", args=[bundle.pk]),
                        bundle.name,
                        bundle.get_status_display(),
                    )
                else:
                    content = format_html(
                        "<p>This page is in the following bundle: {} (Status: {})</p>",
                        bundle.name,
                        bundle.get_status_display(),
                    )
            else:
                content = format_html("<p>{}</p>", "This page is not part of any bundles.")
            return content


class CustomAdminPageChooser(PagesWithDraftsForBundleChooserWidget):
    def get_display_title(self, instance: "Page") -> str:
        title: str = instance.specific_deferred.get_admin_display_title()

        if workflow_state := instance.current_workflow_state:
            title = f"{title} ({workflow_state.current_task_state.task.name})"
        else:
            title = f"{title} (not in a workflow)"

        return title


class PageChooserWithStatusPanel(PageChooserPanel):
    """A custom page chooser panel that includes the page workflow status."""

    def get_form_options(self) -> dict[str, list | dict]:
        opts: dict[str, list | dict] = super().get_form_options()

        if self.page_type or self.can_choose_root:
            widgets = opts.setdefault("widgets", {})
            widgets[self.field_name] = CustomAdminPageChooser()

        return opts

    class BoundPanel(PageChooserPanel.BoundPanel):
        def __init__(self, **kwargs: Any) -> None:
            """Sets the panel heading to the page verbose name to help differentiate page types."""
            super().__init__(**kwargs)
            if page := self.instance.page:
                self.heading = page.specific_deferred.get_verbose_name()
