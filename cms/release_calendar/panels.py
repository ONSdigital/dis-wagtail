from typing import TYPE_CHECKING, Any, Union

from django.urls import reverse
from django.utils.html import format_html
from wagtail.admin.panels import HelpPanel

from cms.bundles.permissions import user_can_manage_bundles

if TYPE_CHECKING:
    from django.utils.safestring import SafeString


class ReleaseCalendarBundleNotePanel(HelpPanel):
    """An extended HelpPanel class."""

    def __init__(
        self,
        content: str = "",
        template: str = "release_calendar/bundle_note_help_panel.html",
        **kwargs: Any,
    ) -> None:
        super().__init__(content=content, template=template, **kwargs)

    class BoundPanel(HelpPanel.BoundPanel):
        def __init__(self, **kwargs: Any) -> None:
            super().__init__(**kwargs)
            self.content = self._get_panel_content()

        @property
        def status(self) -> str:
            if self.instance.active_bundle:
                return "warning" if self.instance.active_bundle.is_ready_to_be_published else "info"
            return ""

        def is_shown(self) -> bool:
            return self.instance.active_bundle is not None

        def _get_panel_content(self) -> Union[str, "SafeString"]:
            if not self.instance.active_bundle:
                return ""

            bundle = self.instance.active_bundle
            if user_can_manage_bundles(self.request.user):
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
