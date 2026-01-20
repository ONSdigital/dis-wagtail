from typing import TYPE_CHECKING, ClassVar

from wagtail.blocks import RichTextBlock, StreamBlock
from wagtail.images.blocks import ImageChooserBlock

from cms.core.blocks import (
    AccordionBlock,
    AnnouncementPanelBlock,
    DocumentsBlock,
    HeadingBlock,
    InformationPanelBlock,
    ONSTableBlock,
    QuoteBlock,
    RelatedLinksBlock,
    VideoEmbedBlock,
    WarningPanelBlock,
)
from cms.core.blocks.equation import EquationBlock
from cms.core.blocks.section_blocks import SectionBlock
from cms.datavis.blocks.charts import IframeBlock

if TYPE_CHECKING:
    from wagtail.blocks import StreamValue


class SectionStoryBlock(StreamBlock):
    """The core section StreamField block definition."""

    section = SectionBlock()

    class Meta:
        template = "templates/components/streamfield/stream_block.html"

    def has_equations(self, value: StreamValue) -> bool:
        """Checks if there are any equation blocks."""
        return any(block.value["content"].first_block_by_name(block_name="equation") is not None for block in value)


class CoreStoryBlock(StreamBlock):
    """The core StreamField block definition."""

    heading = HeadingBlock()
    rich_text = RichTextBlock()
    quote = QuoteBlock()
    warning_panel = WarningPanelBlock()
    information_panel = InformationPanelBlock()
    announcement_panel = AnnouncementPanelBlock()
    accordion = AccordionBlock()
    video_embed = VideoEmbedBlock(group="Media")
    image = ImageChooserBlock(group="Media")
    documents = DocumentsBlock(group="Media")
    related_links = RelatedLinksBlock(add_heading=True)  # Add a heading as this is outside of a section block
    table = ONSTableBlock(group="DataVis", allow_links=True)
    equation = EquationBlock(group="DataVis", icon="decimal")
    iframe_visualisation = IframeBlock(group="DataVis", label="Iframe Visualisation")

    class Meta:
        block_counts: ClassVar[dict[str, dict]] = {"related_links": {"max_num": 1}}
        template = "templates/components/streamfield/stream_block.html"

    def has_equations(self, value: StreamValue) -> bool:
        """Checks if there are any equation blocks."""
        return value.first_block_by_name(block_name="equation") is not None
