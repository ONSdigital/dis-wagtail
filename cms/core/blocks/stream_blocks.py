from typing import ClassVar

from wagtail.blocks import RichTextBlock, StreamBlock
from wagtail.images.blocks import ImageChooserBlock
from wagtailmath.blocks import MathBlock

from cms.core.blocks import (
    DocumentsBlock,
    HeadingBlock,
    ONSEmbedBlock,
    PanelBlock,
    QuoteBlock,
    RelatedLinksBlock,
    VideoEmbedBlock,
)
from cms.core.blocks.section_blocks import SectionBlock
from cms.datavis.blocks import DataVisBlock


class SectionStoryBlock(StreamBlock):
    """The core section StreamField block definition."""

    section = SectionBlock()

    class Meta:
        template = "templates/components/streamfield/stream_block.html"


class CoreStoryBlock(StreamBlock):
    """The core StreamField block definition."""

    heading = HeadingBlock()
    rich_text = RichTextBlock()
    quote = QuoteBlock()
    panel = PanelBlock()
    video_embed = VideoEmbedBlock(group="Media")
    image = ImageChooserBlock(group="Media")
    documents = DocumentsBlock(group="Media")
    related_links = RelatedLinksBlock()
    equation = MathBlock(group="DataVis", icon="decimal")
    datavis = DataVisBlock(group="DataVis", label="Visualisation")
    ons_embed = ONSEmbedBlock(group="DataVis", label="ONS General Embed")

    class Meta:
        block_counts: ClassVar[dict[str, dict]] = {"related_links": {"max_num": 1}}
