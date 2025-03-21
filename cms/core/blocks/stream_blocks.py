from typing import TYPE_CHECKING, ClassVar

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
from cms.datavis.blocks import BarChartBlock, ColumnChartBlock, LineChartBlock

if TYPE_CHECKING:
    from wagtail.blocks import StreamValue


class SectionStoryBlock(StreamBlock):
    """The core section StreamField block definition."""

    section = SectionBlock()

    class Meta:
        template = "templates/components/streamfield/stream_block.html"

    def has_equations(self, value: "StreamValue") -> bool:
        """Checks if there are any equation blocks."""
        return any(block.value["content"].first_block_by_name(block_name="equation") is not None for block in value)

    def has_ons_embed(self, value: "StreamValue") -> bool:
        """Checks if there are any ONS embed blocks."""
        return any(block.value["content"].first_block_by_name(block_name="ons_embed") is not None for block in value)


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
    ons_embed = ONSEmbedBlock(group="DataVis", label="ONS General Embed")

    line_chart = LineChartBlock(group="DataVis", label="Line Chart")
    bar_chart = BarChartBlock(group="DataVis", label="Bar Chart")
    column_chart = ColumnChartBlock(group="DataVis", label="Column Chart")

    class Meta:
        block_counts: ClassVar[dict[str, dict]] = {"related_links": {"max_num": 1}}
        template = "templates/components/streamfield/stream_block.html"

    def has_equations(self, value: "StreamValue") -> bool:
        """Checks if there are any equation blocks."""
        return value.first_block_by_name(block_name="equation") is not None

    def has_ons_embed(self, value: "StreamValue") -> bool:
        """Checks if there are any ONS embed blocks."""
        return value.first_block_by_name(block_name="ons_embed") is not None
