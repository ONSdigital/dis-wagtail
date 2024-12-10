from typing import TYPE_CHECKING, ClassVar

from django.utils.text import slugify
from wagtail.blocks import RichTextBlock, StreamBlock, StructBlock
from wagtail.embeds.blocks import EmbedBlock
from wagtail.images.blocks import ImageChooserBlock
from wagtailmath.blocks import MathBlock

if TYPE_CHECKING:
    from wagtail.blocks import StructValue

from cms.core.blocks import (
    DocumentsBlock,
    HeadingBlock,
    ONSEmbedBlock,
    PanelBlock,
    RelatedContentBlock,
    RelatedLinksBlock,
)


class SectionContentBlock(StreamBlock):
    """The core section content block definition."""

    rich_text = RichTextBlock()
    panel = PanelBlock()
    embed = EmbedBlock(group="Media")
    image = ImageChooserBlock(group="Media")
    documents = DocumentsBlock(group="Media")
    related_links = RelatedLinksBlock(RelatedContentBlock(), icon="link")
    equation = MathBlock(group="DataVis", icon="decimal")
    ons_embed = ONSEmbedBlock(group="DataVis", label="ONS General Embed")

    class Meta:
        template = "templates/components/streamfield/stream_block.html"


class SectionBlock(StructBlock):
    """The core section block definition with headers."""

    title = HeadingBlock()
    content = SectionContentBlock()

    class Meta:
        block_counts: ClassVar[dict[str, dict]] = {"related_links": {"max_num": 1}}
        template = "templates/components/streamfield/section_with_header_block.html"

    def to_table_of_contents_items(self, value: "StructValue") -> list[dict[str, str]]:
        """Convert the value to the table of contents component macro format."""
        return [{"url": "#" + slugify(value["title"]), "text": value["title"]}]


class SectionStreamBlock(StreamBlock):
    """The analysis StreamField block definition."""

    section = SectionBlock()

    class Meta:
        template = "templates/components/streamfield/stream_block.html"
