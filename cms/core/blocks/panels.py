from django.conf import settings
from django.forms import Media
from django.utils.functional import cached_property
from django.utils.translation import gettext_lazy as _
from wagtail import blocks
from wagtail.blocks.field_block import FieldBlockAdapter
from wagtail.telepath import register


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


class PreviousVersionBlock(blocks.IntegerBlock):
    pass


class CorrectionOrNoticeBlock(blocks.StructBlock):
    when = blocks.DateTimeBlock()
    text = blocks.RichTextBlock(features=settings.RICH_TEXT_BASIC)

    class Meta:
        abstract = True


class CorrectionBlock(CorrectionOrNoticeBlock):
    previous_version = PreviousVersionBlock(required=False)

    class Meta:
        template = "templates/components/streamfield/corrections_block.html"
        help_text = "Warning: Reordering or deleting a correction will change its (and others') version number."


class PreviousVersionBlockAdapter(FieldBlockAdapter):
    js_constructor = "cms.core.blocks.panels.PreviousVersionBlock"

    @cached_property
    def media(self):
        structblock_media = super().media
        return Media(js=[*structblock_media._js, "js/previous-version-block.js"], css=structblock_media._css)  # pylint: disable=protected-access


register(PreviousVersionBlockAdapter(), PreviousVersionBlock)


class NoticeBlock(CorrectionOrNoticeBlock):
    class Meta:
        template = "templates/components/streamfield/notices_block.html"
