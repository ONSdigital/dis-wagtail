from django.conf import settings
from django.utils.translation import gettext_lazy as _
from wagtail import blocks


class WarnAnnouncementPanelBlock(blocks.StructBlock):
    """Covers 'warn' and 'announcement' variants. No title is needed."""

    variant = blocks.ChoiceBlock(
        choices=[
            ("warn", _("Warning")),
            ("announcement", _("Announcement")),
        ],
        default="warn",
        label=_("Panel type"),
    )
    body = blocks.RichTextBlock(features=settings.RICH_TEXT_BASIC)

    class Meta:
        template = "templates/components/streamfield/warn_announcement_panel.html"
        label = _("Warning/Announcement Panel")


class InfoErrorSuccessPanelBlock(blocks.StructBlock):
    """Covers 'info', 'error', and 'success' variants, each requiring a title."""

    variant = blocks.ChoiceBlock(
        choices=[
            ("info", _("Information")),
            ("error", _("Error")),
            ("success", _("Success")),
        ],
        default="info",
        label=_("Panel type"),
    )
    body = blocks.RichTextBlock(features=settings.RICH_TEXT_BASIC)
    title = blocks.CharBlock(required=True, label=_("Title"))

    class Meta:
        template = "templates/components/streamfield/info_error_success_panel.html"
        label = _("Info/Error/Success Panel")
