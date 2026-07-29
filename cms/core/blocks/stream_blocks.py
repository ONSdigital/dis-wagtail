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

    def has_block_with_name(self, name: str, value: StreamValue) -> bool:
        """Checks if there are any blocks with the given name."""
        return any(block.value["content"].first_block_by_name(block_name=name) is not None for block in value)

    def has_equations(self, value: StreamValue) -> bool:
        """Checks if there are any equation blocks."""
        return self.has_block_with_name("equation", value)

    def has_iframe_visalisations(self, value: StreamValue) -> bool:
        """Checks if there are any iframe visualisation blocks."""
        return self.has_block_with_name("iframe_visualisation", value)
