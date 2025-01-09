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


class CoreStoryBlock(StreamBlock):
    """The core StreamField block definition."""

    heading = HeadingBlock()
    rich_text = RichTextBlock()
    quote = QuoteBlock()
    panel = PanelBlock()
    video_embed = VideoEmbedBlock(group="Media")
    image = ImageChooserBlock()
    documents = DocumentsBlock()
    related_links = RelatedLinksBlock()
    equation = MathBlock(group="DataVis", icon="decimal")
    ons_embed = ONSEmbedBlock(group="DataVis", label="ONS General Embed")

    class Meta:
        block_counts: ClassVar[dict[str, dict]] = {"related_links": {"max_num": 1}}
