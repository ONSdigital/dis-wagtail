from typing import ClassVar

from wagtail.blocks import RichTextBlock, StreamBlock
from wagtail.embeds.blocks import EmbedBlock
from wagtail.images.blocks import ImageChooserBlock
from wagtailmath.blocks import MathBlock

from cms.core.blocks import (
    DocumentsBlock,
    HeadingBlock,
    ONSEmbedBlock,
    PanelBlock,
    RelatedLinksBlock,
)
from cms.core.blocks.section_blocks import SectionBlock


class SectionStoryBlock(StreamBlock):
    """The core section StreamField block definition."""

    section = SectionBlock()

    class Meta:
        template = "templates/components/streamfield/stream_block.html"


class CoreStoryBlock(StreamBlock):
    """The core StreamField block definition."""

    heading = HeadingBlock()
    rich_text = RichTextBlock()
    panel = PanelBlock()
    embed = EmbedBlock(group="Media")
    image = ImageChooserBlock(group="Media")
    documents = DocumentsBlock(group="Media")
    related_links = RelatedLinksBlock()
    equation = MathBlock(group="DataVis", icon="decimal")
    ons_embed = ONSEmbedBlock(group="DataVis", label="ONS General Embed")

    class Meta:
        block_counts: ClassVar[dict[str, dict]] = {"related_links": {"max_num": 1}}
