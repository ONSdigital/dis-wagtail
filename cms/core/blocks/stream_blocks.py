from wagtail.blocks import StreamBlock

from cms.core.blocks.section_blocks import SectionBlock


class SectionStoryBlock(StreamBlock):
    """The analysis StreamField block definition."""

    section = SectionBlock()

    class Meta:
        template = "templates/components/streamfield/stream_block.html"
