from django.conf import settings
from django.forms import Media
from django.utils.functional import cached_property
from wagtail import blocks
from wagtail.admin.telepath import register
from wagtail.blocks.field_block import FieldBlockAdapter
from wagtail.blocks.struct_block import StructBlockAdapter


class BasePanelBlock(blocks.StructBlock):
    """A reusable base panel block with a body field.
    Subclasses can override Meta attributes (e.g., template, label)
    and define additional fields as needed.
    """

    body = blocks.RichTextBlock(features=settings.RICH_TEXT_BASIC)

    class Meta:
        abstract = True
        group = "Panels"


class WarningPanelBlock(BasePanelBlock):
    class Meta:
        template = "templates/components/streamfield/warning_panel.html"
        icon = "warning"
        label = "Warning Panel"


class AnnouncementPanelBlock(BasePanelBlock):
    class Meta:
        template = "templates/components/streamfield/announcement_panel.html"
        icon = "pick"
        label = "Announcement Panel"


class InformationPanelBlock(BasePanelBlock):
    class Meta:
        template = "templates/components/streamfield/information_panel.html"
        icon = "info-circle"
        label = "Information Panel"


class PreviousVersionBlock(blocks.IntegerBlock):
    pass


class CorrectionOrNoticeBlock(blocks.StructBlock):
    when = blocks.DateTimeBlock()
    text = blocks.RichTextBlock(features=settings.RICH_TEXT_BASIC)

    class Meta:
        abstract = True


class CorrectionBlock(CorrectionOrNoticeBlock):
    previous_version = PreviousVersionBlock(required=False)
    frozen = blocks.BooleanBlock(required=False, default=False)
    version_id = blocks.IntegerBlock(required=False)

    class Meta:
        help_text = "Warning: Once a correction is published, it cannot be deleted."


class CorrectionBlockAdapter(StructBlockAdapter):
    js_constructor = "cms.core.blocks.panels.CorrectionBlock"

    @cached_property
    def media(self) -> Media:
        structblock_media = super().media
        return Media(
            js=[
                *structblock_media._js,  # pylint: disable=protected-access
                "js/blocks/readonly-struct-block.js",
                "js/blocks/correction-block.js",
            ],
            css=structblock_media._css,  # pylint: disable=protected-access
        )


register(CorrectionBlockAdapter(), CorrectionBlock)


class PreviousVersionBlockAdapter(FieldBlockAdapter):
    js_constructor = "cms.core.blocks.panels.PreviousVersionBlock"

    @cached_property
    def media(self) -> Media:
        structblock_media = super().media
        return Media(js=[*structblock_media._js, "js/blocks/previous-version-block.js"], css=structblock_media._css)  # pylint: disable=protected-access


register(PreviousVersionBlockAdapter(), PreviousVersionBlock)


class NoticeBlock(CorrectionOrNoticeBlock):
    when = blocks.DateBlock()
