from typing import TYPE_CHECKING, Any

from django.utils.text import slugify
from django.utils.translation import gettext as _
from wagtail.blocks import CharBlock, ListBlock

from .base import LinkBlock

if TYPE_CHECKING:
    from wagtail.blocks.list_block import ListValue


class RelatedContentBlock(LinkBlock):
    """Related content block with page or link validation."""

    description = CharBlock(required=False)


class RelatedLinksBlock(ListBlock):
    """Defines a list of links block."""

    def __init__(self, search_index: bool = True, **kwargs: Any) -> None:
        super().__init__(RelatedContentBlock, search_index=search_index, **kwargs)

        self.heading = _("Related links")
        self.slug = slugify(self.heading)

    def get_context(self, value: "ListValue", parent_context: dict | None = None) -> dict:
        """Inject our block heading and slug in the template context."""
        context: dict = super().get_context(value, parent_context=parent_context)
        context["heading"] = self.heading
        context["slug"] = self.slug

        context["related_links"] = [item.get_related_link(context=context) for item in value]

        return context

    class Meta:
        icon = "list-ul"
        template = "templates/components/streamfield/related_links_block.html"

    def to_table_of_contents_items(self, _value: "ListValue") -> list[dict[str, str]]:
        """Returns the table of contents component macro data."""
        return [{"url": "#" + self.slug, "text": self.heading}]
