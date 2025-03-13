from typing import TYPE_CHECKING, ClassVar

from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _
from wagtail.blocks import RichTextBlock, StreamBlock, StructBlock
from wagtail.images.blocks import ImageChooserBlock
from wagtailmath.blocks import MathBlock

from cms.core.blocks import (
    AnnouncementPanelBlock,
    DocumentsBlock,
    HeadingBlock,
    InformationPanelBlock,
    ONSEmbedBlock,
    QuoteBlock,
    RelatedLinksBlock,
    VideoEmbedBlock,
    WarningPanelBlock,
)
from cms.core.blocks.glossary_terms import GlossaryTermsBlock
from cms.core.blocks.markup import ONSTableBlock

if TYPE_CHECKING:
    from wagtail.blocks import StructValue


class SectionContentBlock(StreamBlock):
    """The core section content block definition."""

    rich_text = RichTextBlock()
    quote = QuoteBlock()
    warning_panel = WarningPanelBlock()
    information_panel = InformationPanelBlock()
    announcement_panel = AnnouncementPanelBlock()
    image = ImageChooserBlock(group="Media")
    documents = DocumentsBlock(group="Media")
    video_embed = VideoEmbedBlock(group="Media")
    table = ONSTableBlock(group="DataVis", allow_links=True)
    equation = MathBlock(group="DataVis", icon="decimal")
    ons_embed = ONSEmbedBlock(group="DataVis", label=_("ONS General Embed"))
    related_links = RelatedLinksBlock(icon="link")
    definitions = GlossaryTermsBlock()

    class Meta:
        template = "templates/components/streamfield/stream_block.html"
        block_counts: ClassVar[dict[str, dict]] = {"related_links": {"max_num": 1}}


class SectionBlock(StructBlock):
    """The core section block definition with headers."""

    title = HeadingBlock()
    content = SectionContentBlock()

    class Meta:
        template = "templates/components/streamfield/section_block.html"

    def to_table_of_contents_items(self, value: "StructValue") -> list[dict[str, str]]:
        """Convert the value to the table of contents component macro format."""
        return [{"url": "#" + slugify(value["title"]), "text": value["title"]}]
