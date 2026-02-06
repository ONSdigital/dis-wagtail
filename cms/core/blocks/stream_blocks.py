from typing import TYPE_CHECKING

from wagtail.blocks import StreamBlock

from cms.core.blocks.section_blocks import SectionBlock

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
