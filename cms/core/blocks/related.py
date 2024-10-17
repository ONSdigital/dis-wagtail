from functools import cached_property

from django.core.exceptions import ValidationError
from django.forms.utils import ErrorList
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


class LinkBlockStructValue(StructValue):
    @cached_property
    def link(self) -> dict | None:  # pylint: disable=inconsistent-return-statements
        title = self.get("title")
        desc = self.get("description")
        if external_url := self.get("external_url"):
            return {"url": external_url, "text": title, "description": desc}

        if (page := self.get("page")) and page.live:
            return {
                "url": page.url,
                "text": title or page,
                "description": desc or getattr(page.specific_deferred, "summary", ""),
            }


class RelatedContentBlock(StructBlock):
    page = PageChooserBlock(required=False)
    external_url = URLBlock(required=False, label="or External Link")
    title = CharBlock(
        help_text="Populate when adding an external link. "
        "When choosing a page, you can leave it blank to use the page's own title",
        required=False,
    )
    description = CharBlock(required=False)

    class Meta:
        icon = "link"
        value_class = LinkBlockStructValue

    def clean(self, value):
        value = super().clean(value)
        page = value["page"]
        external_url = value["external_url"]
        errors = {}
        non_block_errors = ErrorList()

        # Require exactly one link
        if not page and not external_url:
            error = ValidationError("Either Page or External Link is required.", code="invalid")
            errors["page"] = ErrorList([error])
            errors["external_url"] = ErrorList([error])
            non_block_errors.append(ValidationError("Missing required fields"))
        elif page and external_url:
            error = ValidationError("Please select either a page or a URL, not both.", code="invalid")
            errors["page"] = ErrorList([error])
            errors["external_url"] = ErrorList([error])

        # Require title for external links
        if not page and external_url and not value["title"]:
            errors["title"] = ErrorList([ValidationError("Title is required for external links.", code="invalid")])

        if errors:
            raise StreamBlockValidationError(block_errors=errors, non_block_errors=non_block_errors)

        return value


class RelatedLinksBlock(ListBlock):
    def __init__(self, child_block, search_index=True, **kwargs):
        super().__init__(child_block, search_index=search_index, **kwargs)

        self.heading = _("Related links")
        self.slug = slugify(self.heading)

    def get_context(self, value, parent_context=None):
        context = super().get_context(value, parent_context=parent_context)
        context["heading"] = self.heading
        context["slug"] = self.slug

        return context

    class Meta:
        icon = "list-ul"
        template = "templates/components/streamfield/related_links_block.html"

    def to_table_of_contents_items(self, value):  # pylint: disable=unused-argument
        return [{"url": "#" + self.slug, "text": self.heading}]
