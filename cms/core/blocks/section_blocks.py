from typing import TYPE_CHECKING, ClassVar

from django.utils.text import slugify
from wagtail.blocks import RichTextBlock, StreamBlock, StructBlock

from cms.core.blocks import (
    AccordionBlock,
    AnnouncementPanelBlock,
    DocumentsBlock,
    HeadingBlock,
    InformationPanelBlock,
    QuoteBlock,
    RelatedLinksBlock,
    VideoEmbedBlock,
    WarningPanelBlock,
)
from cms.core.blocks.definitions import DefinitionsBlock
from cms.core.blocks.embeddable import ImageBlock
from cms.core.blocks.equation import EquationBlock
from cms.core.blocks.markup import ONSTableBlock
from cms.datavis.blocks import (
    AreaChartBlock,
    BarColumnChartBlock,
    BarColumnConfidenceIntervalChartBlock,
    IframeBlock,
    LineChartBlock,
    ScatterPlotBlock,
)

if TYPE_CHECKING:
    from wagtail.blocks import StructValue


class SectionContentBlock(StreamBlock):
    """The core section content block definition."""

    rich_text = RichTextBlock()
    quote = QuoteBlock()
    warning_panel = WarningPanelBlock()
    information_panel = InformationPanelBlock()
    announcement_panel = AnnouncementPanelBlock()
    accordion = AccordionBlock()
    image = ImageBlock(group="Media")
    documents = DocumentsBlock(group="Media")
    video_embed = VideoEmbedBlock(group="Media")
    table = ONSTableBlock(group="DataVis", allow_links=True)
    equation = EquationBlock(group="DataVis", icon="decimal")
    related_links = RelatedLinksBlock(icon="link")
    definitions = DefinitionsBlock()

    line_chart = LineChartBlock(group="DataVis", label="Line Chart")
    bar_column_chart = BarColumnChartBlock(group="DataVis", label="Bar/Column Chart")
    bar_column_confidence_interval_chart = BarColumnConfidenceIntervalChartBlock(
        group="DataVis", label="Bar/Column Chart with Confidence Intervals"
    )
    scatter_plot = ScatterPlotBlock(group="DataVis", label="Scatter Plot")
    area_chart = AreaChartBlock(group="DataVis", label="Area Chart")
    iframe_visualisation = IframeBlock(group="DataVis", label="Iframe Visualisation")

    class Meta:
        template = "templates/components/streamfield/stream_block.html"
        block_counts: ClassVar[dict[str, dict]] = {"related_links": {"max_num": 1}}


class SectionBlock(StructBlock):
    """The core section block definition with headers."""

    title = HeadingBlock()
    content = SectionContentBlock()

    class Meta:
        template = "templates/components/streamfield/section_block.html"

    def to_table_of_contents_items(self, value: StructValue) -> list[dict[str, str]]:
        """Convert the value to the table of contents component macro format."""
        return [{"url": "#" + slugify(value["title"]), "text": value["title"]}]


class CoreSectionContentBlock(StreamBlock):
    """The core section content block definition."""

    heading = HeadingBlock()
    rich_text = RichTextBlock()
    quote = QuoteBlock()
    warning_panel = WarningPanelBlock()
    information_panel = InformationPanelBlock()
    announcement_panel = AnnouncementPanelBlock()
    accordion = AccordionBlock()
    video_embed = VideoEmbedBlock(group="Media")
    image = ImageBlock(group="Media")
    documents = DocumentsBlock(group="Media")
    related_links = RelatedLinksBlock()
    table = ONSTableBlock(group="DataVis", allow_links=True)
    equation = EquationBlock(group="DataVis", icon="decimal")
    iframe_visualisation = IframeBlock(group="DataVis", label="Iframe Visualisation")

    class Meta:
        block_counts: ClassVar[dict[str, dict]] = {"related_links": {"max_num": 1}}
        template = "templates/components/streamfield/stream_block.html"


class CoreSectionBlock(StructBlock):
    """The core section block definition with headers."""

    title = HeadingBlock()
    content = CoreSectionContentBlock()

    class Meta:
        template = "templates/components/streamfield/section_block.html"

    def to_table_of_contents_items(self, value: StructValue) -> list[dict[str, str]]:
        """Convert the value to the table of contents component macro format."""
        return [{"url": "#" + slugify(value["title"]), "text": value["title"]}]
