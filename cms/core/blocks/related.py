from typing import TYPE_CHECKING, Any

from django.forms import ValidationError
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _
from wagtail.blocks import CharBlock, ChoiceBlock, DateBlock, ListBlock, StructBlockValidationError

from cms.core.blocks.base import LinkBlock
from cms.core.enums import RelatedContentType

if TYPE_CHECKING:
    from django_stubs_ext import StrOrPromise
    from wagtail.blocks.list_block import ListValue

    from cms.core.blocks.base import LinkBlockStructValue


class LinkBlockWithDescription(LinkBlock):
    description = CharBlock(required=False)


class RelatedContentBlock(LinkBlockWithDescription):
    """Related content block with page or link validation."""

    content_type = ChoiceBlock(
        choices=RelatedContentType.choices,
        help_text="Select the type of related content.",
        required=False,
    )
    release_date = DateBlock(required=False)

    def clean(self, value: LinkBlockStructValue) -> LinkBlockStructValue:
        """Validate the related content based on its type."""
        cleaned_value = super().clean(value)

        errors = {}

        if cleaned_value["external_url"] and not cleaned_value["content_type"]:
            errors["content_type"] = ValidationError("You must select a content type when providing an external URL.")

        if errors:
            raise StructBlockValidationError(block_errors=errors)

        return cleaned_value


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

    def get_context(self, value: ListValue, parent_context: dict | None = None) -> dict:
        """Inject our block heading and slug in the template context."""
        context: dict = super().get_context(value, parent_context=parent_context)
        context["related_links"] = [item.get_related_link(context=context) for item in value]

        if self.heading:
            context["heading"] = self.heading
            context["slug"] = self.slug
            for position, link in enumerate(context["related_links"], start=1):
                link["attributes"]["data-ga-section-title"] = self.heading
                link["attributes"]["data-ga-click-position"] = position

        return context

    class Meta:
        icon = "list-ul"
        help_text = "A list of related links."
        template = "templates/components/streamfield/related_links_block.html"

    def to_table_of_contents_items(self, _value: ListValue) -> list[dict[str, StrOrPromise]]:
        """Returns the table of contents component macro data."""
        return [{"url": "#" + self.slug, "text": self.heading}]
