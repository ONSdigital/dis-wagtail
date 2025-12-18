from typing import TYPE_CHECKING, Any

from django.conf import settings
from django.templatetags.static import static
from django.urls import reverse
from django.utils.html import format_html
from wagtail import hooks
from wagtail.admin import messages
from wagtail.log_actions import LogFormatter
from wagtail.snippets.models import register_snippet

from cms.core.viewsets import ContactDetailsViewSet, GlossaryViewSet

if TYPE_CHECKING:
    from django.http import HttpRequest
    from wagtail.log_actions import LogActionRegistry
    from wagtail.models import ModelLogEntry, Page


@hooks.register("register_icons")
def register_icons(icons: list[str]) -> list[str]:
    """Registers custom icons.

    Sources:
    - https://service-manual.ons.gov.uk/brand-guidelines/iconography/icon-set
    """
    return [
        *icons,
        "boxes-stacked.svg",
        "data-analysis.svg",
        "identity.svg",
        "news.svg",
        "wagtailfontawesomesvg/solid/chart-bar.svg",
        "wagtailfontawesomesvg/solid/chart-column.svg",
        "wagtailfontawesomesvg/solid/chart-line.svg",
        "wagtailfontawesomesvg/solid/chart-area.svg",
        "wagtailfontawesomesvg/solid/table-cells.svg",
        "wagtailfontawesomesvg/solid/location-crosshairs.svg",
        "wagtailfontawesomesvg/solid/square.svg",
    ]


@hooks.register("insert_editor_js")
def editor_js() -> str:
    """Modify the default behavior of the Wagtail admin editor."""
    return format_html('<script src="{}"></script>', static("js/wagtail-editor-customisations.js"))


@hooks.register("insert_global_admin_css")
def global_admin_css() -> str:
    return format_html('<link rel="stylesheet" href="{}">', static("css/admin.css"))


register_snippet(ContactDetailsViewSet)
register_snippet(GlossaryViewSet)


@hooks.register("after_edit_page")
def after_edit_page(request: "HttpRequest", page: "Page") -> None:
    if page.locale.language_code != settings.LANGUAGE_CODE:
        return

    # Check if proper translations of the page exist, which are not simple aliases
    proper_translation = page.get_translations().filter(alias_of__isnull=True).only("id").first()
    if proper_translation:
        admin_edit_url = reverse("wagtailadmin_pages:edit", args=[proper_translation.id])
        messages.warning(
            request,
            "A translated version of this page exists. If you make any changes, please make sure to update it.",
            buttons=[
                messages.button(admin_edit_url, "Go to translation"),
            ],
            extra_tags="safe",
        )


@hooks.register("register_log_actions")
def register_core_log_actions(actions: "LogActionRegistry") -> None:
    """Registers custom logging actions for core content operations.

    @see https://docs.wagtail.org/en/stable/extending/audit_log.html
    @see https://docs.wagtail.org/en/stable/reference/hooks.html#register-log-actions
    """

    @actions.register_action("content.chart_download")
    class ChartDownload(LogFormatter):  # pylint: disable=unused-variable
        """LogFormatter class for chart CSV download actions."""

        label = "Download chart CSV"

        def format_message(self, log_entry: "ModelLogEntry") -> Any:
            """Returns the formatted log message."""
            try:
                chart_id = log_entry.data.get("chart_id", "unknown")
                return f"Downloaded chart CSV (chart ID: {chart_id})"
            except (KeyError, AttributeError):
                return "Downloaded chart CSV"
