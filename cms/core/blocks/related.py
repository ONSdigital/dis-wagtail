from typing import TYPE_CHECKING, Any

from django.core.exceptions import ValidationError
from django.forms.utils import ErrorList
from django.utils.functional import cached_property
from django.utils.text import slugify
from django.utils.translation import gettext as _
from wagtail.blocks import (
    CharBlock,
    ListBlock,
    PageChooserBlock,
    StreamBlockValidationError,
    StructBlock,
    StructValue,
    URLBlock,
)

if TYPE_CHECKING:
    from wagtail.blocks.list_block import ListValue


class LinkBlockStructValue(StructValue):
    """Custom StructValue for link blocks."""

    @cached_property
    def link(self) -> dict | None:
        """A convenience property that returns the block value in a consistent way,
        regardless of the chosen values (be it a Wagtail page or external link).
        """
        value = None
        title = self.get("title")
        desc = self.get("description")
        has_description = "description" in self

        if external_url := self.get("external_url"):
            value = {"url": external_url, "text": title}
            if has_description:
                value["description"] = desc

        if (page := self.get("page")) and page.live:
            value = {"url": page.url, "text": title or page.title}
            if has_description:
                value["description"] = desc or getattr(page.specific_deferred, "summary", "")

        return value


class LinkBlock(StructBlock):
    """Related link block with page or link validation."""

    page = PageChooserBlock(required=False)
    external_url = URLBlock(required=False, label="or External Link")
    title = CharBlock(
        help_text="Populate when adding an external link. "
        "When choosing a page, you can leave it blank to use the page's own title",
        required=False,
    )

    class Meta:  # pylint: disable=missing-class-docstring
        icon = "link"
        value_class = LinkBlockStructValue

    def clean(self, value: LinkBlockStructValue) -> LinkBlockStructValue:
        """Validate that either a page or external link is provided, and that external links have a title."""
        value = super().clean(value)
        page = value["page"]
        external_url = value["external_url"]
        errors = {}
        non_block_errors = ErrorList()

        # Require exactly one link
        if not page and not external_url:
            error = ValidationError(_("Either Page or External Link is required."), code="invalid")
            errors["page"] = ErrorList([error])
            errors["external_url"] = ErrorList([error])
            non_block_errors.append(ValidationError(_("Missing required fields")))
        elif page and external_url:
            error = ValidationError(_("Please select either a page or a URL, not both."), code="invalid")
            errors["page"] = ErrorList([error])
            errors["external_url"] = ErrorList([error])

        # Require title for external links
        if not page and external_url and not value["title"]:
            errors["title"] = ErrorList([ValidationError(_("Title is required for external links."), code="invalid")])

        if errors:
            raise StreamBlockValidationError(block_errors=errors, non_block_errors=non_block_errors)

        return value


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

        return context

    class Meta:  # pylint: disable=missing-class-docstring
        icon = "list-ul"
        template = "templates/components/streamfield/related_links_block.html"

    def to_table_of_contents_items(self, _value: "ListValue") -> list[dict[str, str]]:
        """Returns the table of contents component macro data."""
        return [{"url": "#" + self.slug, "text": self.heading}]
