from typing import TYPE_CHECKING, Any, Union

from django.utils.html import format_html, format_html_join
from wagtail.admin.panels import HelpPanel, PageChooserPanel
from wagtail.admin.widgets import AdminPageChooser

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
            if not hasattr(instance, "bundles"):
                return ""

            if bundles := instance.bundles:
                content_html = format_html_join(
                    "\n",
                    "<li>{} (Status: {})</li>",
                    (
                        (
                            bundle.name,
                            bundle.get_status_display(),
                        )
                        for bundle in bundles
                    ),
                )

                content = format_html("<p>{}</p><ul>{}</ul>", "This page is in the following bundle(s):", content_html)
            else:
                content = format_html("<p>{}</p>", "This page is not part of any bundles.")
            return content


class CustomAdminPageChooser(AdminPageChooser):
    def get_display_title(self, instance: "Page") -> str:
        title: str = super().get_display_title(instance)

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
            widgets[self.field_name] = CustomAdminPageChooser(
                target_models=self.page_type, can_choose_root=self.can_choose_root
            )

        return opts

    class BoundPanel(PageChooserPanel.BoundPanel):
        def __init__(self, **kwargs: Any) -> None:
            """Sets the panel heading to the page verbose name to help differentiate page types."""
            super().__init__(**kwargs)
            if page := self.instance.page:
                self.heading = page.specific.get_verbose_name()
