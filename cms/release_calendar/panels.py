from datetime import datetime
from typing import TYPE_CHECKING, Any, Union

from django.conf import settings
from django.urls import reverse
from django.utils.html import format_html
from django.utils.timezone import is_aware, localtime
from wagtail.admin.panels import FieldPanel, HelpPanel
from wagtail.admin.widgets.datetime import DEFAULT_DATETIME_FORMAT

from cms.bundles.permissions import user_can_manage_bundles

if TYPE_CHECKING:
    from django.utils.safestring import SafeString
    from laces.typing import RenderContext


class ReleaseCalendarBundleNotePanel(HelpPanel):
    """An extended HelpPanel class."""

    def __init__(
        self,
        content: str = "",
        template: str = "wagtailadmin/panels/bundle_note_help_panel.html",
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

        def _get_panel_content(self) -> Union[str, SafeString]:
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


class ChangesToReleaseDateFieldPanel(FieldPanel):
    """FieldPanel that injects the current release_date from the database into the template
    as previous_release_date, allowing the field to be auto-populated on the client side.

    Note: This panel is only displayed in the form after the page has been initially saved.
    """

    class BoundPanel(FieldPanel.BoundPanel):
        template_name = "wagtailadmin/panels/previous_release_date_data.html"

        def get_context_data(self, parent_context: RenderContext | None = None) -> RenderContext | None:
            # To avoid circular import
            # pylint: disable=cyclic-import,import-outside-toplevel
            from cms.release_calendar.models import ReleaseCalendarPage

            context = super().get_context_data(parent_context)

            context["previous_release_date"] = None

            release_date = (
                ReleaseCalendarPage.objects.filter(pk=self.instance.pk).values_list("release_date", flat=True).first()
            )

            if not release_date:
                return context

            if isinstance(release_date, datetime) and is_aware(release_date):
                release_date = localtime(release_date)

            # Convert the release date to the format required by the form in Wagtail
            context["previous_release_date"] = release_date.strftime(
                getattr(settings, "WAGTAIL_DATETIME_FORMAT", DEFAULT_DATETIME_FORMAT)
            )
            return context
