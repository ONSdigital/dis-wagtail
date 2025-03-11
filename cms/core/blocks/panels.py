from django.conf import settings
from django.utils.translation import gettext_lazy as _
from wagtail import blocks


class BasePanelBlock(blocks.StructBlock):
    """A reusable base panel block with a body field.
    Subclasses can override Meta attributes (e.g., template, label)
    and define additional fields as needed.
    """

    body = blocks.RichTextBlock(features=settings.RICH_TEXT_BASIC)

    class Meta:
        abstract = True
        group = _("Panels")


class WarningPanelBlock(BasePanelBlock):
    class Meta:
        template = "templates/components/streamfield/warning_panel.html"
        icon = "warning"
        label = _("Warning Panel")


class AnnouncementPanelBlock(BasePanelBlock):
    class Meta:
        template = "templates/components/streamfield/announcement_panel.html"
        icon = "pick"
        label = _("Announcement Panel")


class InformationPanelBlock(BasePanelBlock):
    title = blocks.CharBlock(required=True, label=_("Title"))

    class Meta:
        template = "templates/components/streamfield/information_panel.html"
        icon = "info-circle"
        label = _("Information Panel")
