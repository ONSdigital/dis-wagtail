from django.conf import settings
from django.utils.translation import gettext_lazy as _
from wagtail import blocks


class PanelBlock(blocks.StructBlock):
    """DS Panel block.
    https://service-manual.ons.gov.uk/design-system/components/panel
    https://service-manual.ons.gov.uk/design-system/components/announcement-panel
    https://service-manual.ons.gov.uk/design-system/components/success-panel
    https://service-manual.ons.gov.uk/design-system/components/warning-panels.
    """

    variant = blocks.ChoiceBlock(
        choices=[
            ("warn", _("Warning")),
            ("info", _("Information")),
            ("announcement", "Announcement"),
            ("error", "Error"),
            ("success", "Success"),
        ],
        default="warn",
    )
    body = blocks.RichTextBlock(features=settings.RICH_TEXT_BASIC)
    title = blocks.CharBlock(required=False, label=_("Title (optional)"))

    class Meta:
        label = _("Warning or information panel")
        template = "templates/components/streamfield/panel_block.html"
