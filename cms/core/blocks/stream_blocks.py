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
    RelatedContentBlock,
    RelatedLinksBlock,
)


class CoreStoryBlock(StreamBlock):
    heading = HeadingBlock()
    rich_text = RichTextBlock()
    panel = PanelBlock()
    embed = EmbedBlock()
    image = ImageChooserBlock()
    documents = DocumentsBlock()
    related_links = RelatedLinksBlock(RelatedContentBlock())
    equation = MathBlock(group="DataVis", icon="decimal")
    ons_embed = ONSEmbedBlock(group="DataVis", label="ONS General Embed")

    class Meta:
        block_counts: ClassVar[dict[str, dict]] = {"related_links": {"max_num": 1}}
