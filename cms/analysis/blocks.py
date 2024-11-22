from typing import TYPE_CHECKING, ClassVar

from django.utils.text import slugify
from wagtail.blocks import RichTextBlock, StreamBlock, StructBlock
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

if TYPE_CHECKING:
    from wagtail.blocks import StructValue


class SectionContentBlock(StreamBlock):
    """The analysis section content StreamField block definition."""

    rich_text = RichTextBlock()
    panel = PanelBlock()
    image = ImageChooserBlock(group="Media")
    documents = DocumentsBlock(group="Media")
    embed = EmbedBlock(group="Media")
    equation = MathBlock(group="DataVis", icon="decimal")
    ons_embed = ONSEmbedBlock(group="DataVis", label="ONS General Embed")
    related_links = RelatedLinksBlock(RelatedContentBlock(), icon="link")

    class Meta:
        template = "templates/components/streamfield/stream_block.html"
        block_counts: ClassVar[dict[str, dict]] = {"related_links": {"max_num": 1}}


class SectionBlock(StructBlock):
    """The analysis section block definition."""

    title = HeadingBlock()
    content = SectionContentBlock()

    def to_table_of_contents_items(self, value: "StructValue") -> list[dict[str, str]]:
        """Convert the value to the table of contents component macro format."""
        return [{"url": "#" + slugify(value["title"]), "text": value["title"]}]

    class Meta:
        template = "templates/components/streamfield/analysis_section_block.html"


class AnalysisStoryBlock(StreamBlock):
    """The analysis StreamField block definition."""

    section = SectionBlock()

    class Meta:
        template = "templates/components/streamfield/stream_block.html"
