from typing import TYPE_CHECKING, ClassVar

from django.conf import settings
from django.forms import Media
from django.utils.functional import cached_property
from django.utils.text import slugify
from wagtail import blocks
from wagtail.admin.telepath import register
from wagtail.blocks.struct_block import StructBlockAdapter

from cms.core.blocks import BasicTableBlock, LinkBlock, LinkBlockWithDescription

if TYPE_CHECKING:
    from wagtail.blocks import StructValue
    from wagtail.blocks.list_block import ListValue


class ContentSectionBlock(blocks.StructBlock):
    """A content section with list of links."""

    title = blocks.CharBlock(label="Section title")
    links = blocks.ListBlock(LinkBlockWithDescription())

    class Meta:
        template = "templates/components/streamfield/release_content_section.html"

    def get_context(self, value: "ListValue", parent_context: dict | None = None) -> dict:
        """Inject our block heading and slug in the template context."""
        context: dict = super().get_context(value, parent_context=parent_context)
        context["related_links"] = [item.get_related_link(context=context) for item in value["links"]]

        return context

    def to_table_of_contents_items(self, value: "StructValue") -> list[dict[str, str]]:
        """Convert the value to the table of contents component macro format."""
        return [{"url": "#" + slugify(value["title"]), "text": value["title"]}]


class ReleaseDateChangeBlock(blocks.StructBlock):
    """A block for logging release date changes."""

    previous_date = blocks.DateTimeBlock()
    reason_for_change = blocks.TextBlock()
    frozen = blocks.BooleanBlock(required=False, default=False)

    class Meta:
        template = "templates/components/streamfield/release_date_change_block.html"
        help_text = "Warning: Once a release date change is published, it cannot be deleted."


class ReleaseDateChangeBlockAdapter(StructBlockAdapter):
    js_constructor = "cms.release_calendar.blocks.ReleaseDateChangeBlock"

    @cached_property
    def media(self) -> Media:
        structblock_media = super().media
        return Media(
            js=[
                *structblock_media._js,  # pylint: disable=protected-access
                "js/blocks/readonly-struct-block.js",
                "js/blocks/release-date-change-block.js",
            ],
            css=structblock_media._css,  # pylint: disable=protected-access
        )


register(ReleaseDateChangeBlockAdapter(), ReleaseDateChangeBlock)


class ReleaseCalendarStoryBlock(blocks.StreamBlock):
    """The release calendar page StreamField block."""

    release_content = ContentSectionBlock()

    class Meta:
        template = "templates/components/streamfield/stream_block.html"


class ReleaseCalendarChangesStoryBlock(blocks.StreamBlock):
    """The StreamField block for the release calendar date changes log."""

    date_change_log = ReleaseDateChangeBlock()

    class Meta:
        template = "templates/components/streamfield/stream_block.html"


class ReleaseCalendarPreReleaseAccessStoryBlock(blocks.StreamBlock):
    """The pre-release access information StreamField definition."""

    description = blocks.RichTextBlock(features=settings.RICH_TEXT_BASIC)
    table = BasicTableBlock()

    class Meta:
        template = "templates/components/streamfield/stream_block.html"
        block_counts: ClassVar[dict[str, dict[str, int]]] = {
            "description": {"max_num": 1},
            "table": {"max_num": 1},
        }


class ReleaseCalendarRelatedLinksStoryBlock(blocks.StreamBlock):
    """The 'You might also be interested in' StreamField definition."""

    link = LinkBlock()

    class Meta:
        template = "templates/components/streamfield/stream_block--related-links.html"
