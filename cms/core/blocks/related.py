from typing import TYPE_CHECKING, Any

from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _
from wagtail.blocks import CharBlock, ChoiceBlock, DateBlock, ListBlock

from cms.core.enums import RelatedContentType

from .base import LinkBlock

if TYPE_CHECKING:
    from django_stubs_ext import StrOrPromise
    from wagtail.blocks.list_block import ListValue


class RelatedContentBlock(LinkBlock):
    """Related content block with page or link validation."""

    description = CharBlock(required=False)
    content_type = ChoiceBlock(
        choices=RelatedContentType.choices,
        default=RelatedContentType.ARTICLE,
        help_text="Select the type of related content.",
    )
    release_date = DateBlock(required=False)


class RelatedLinksBlock(ListBlock):
    """Defines a list of links block."""

    def __init__(self, search_index: bool = True, add_heading: bool = False, **kwargs: Any) -> None:
        """Related links block.

        Args:
            search_index (bool, optional): Whether to index the block for search.
            add_heading (bool, optional): Whether to add a "Related links" heading to the block.
            **kwargs: Additional keyword arguments to pass to the ListBlock constructor.
        """
        super().__init__(RelatedContentBlock, search_index=search_index, **kwargs)

        self.heading = _("Related links") if add_heading else ""
        self.slug = slugify(self.heading) if add_heading else ""

    def get_context(self, value: "ListValue", parent_context: dict | None = None) -> dict:
        """Inject our block heading and slug in the template context."""
        context: dict = super().get_context(value, parent_context=parent_context)
        context["related_links"] = [item.get_related_link(context=context) for item in value]

        if self.heading:
            context["heading"] = self.heading
            context["slug"] = self.slug

        return context

    class Meta:
        icon = "list-ul"
        help_text = "A list of related links."
        template = "templates/components/streamfield/related_links_block.html"

    def to_table_of_contents_items(self, _value: "ListValue") -> list[dict[str, "StrOrPromise"]]:
        """Returns the table of contents component macro data."""
        return [{"url": "#" + self.slug, "text": self.heading}]
