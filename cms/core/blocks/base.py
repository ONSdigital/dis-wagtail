from datetime import date, datetime
from typing import Any

from django.core.exceptions import ValidationError
from django.forms.utils import ErrorList
from django.utils.functional import cached_property
from wagtail.blocks import (
    CharBlock,
    PageChooserBlock,
    StreamBlockValidationError,
    StructBlock,
    StructValue,
    URLBlock,
)

from cms.core.utils import get_content_type_for_page, get_document_metadata_date, get_related_content_type_label


class LinkBlockStructValue(StructValue):
    """Custom StructValue for link blocks."""

    def get_link(self, context: dict | None = None) -> dict[str, str | dict[str, Any]] | None:
        """A convenience property that returns the block value in a consistent way,
        regardless of the chosen values (be it a Wagtail page or external link).
        """
        value = None
        content_type_label = None
        page_release_date = None
        title = self.get("title")
        desc = self.get("description")
        has_description = "description" in self

        if external_url := self.get("external_url"):
            value = {"url": external_url, "text": title}
            if has_description:
                value["description"] = desc

        if (page := self.get("page")) and page.live:
            page = page.specific_deferred
            value = {
                "url": page.get_url(request=context.get("request") if context else None),
                "text": title or getattr(page, "display_title", page.title),
            }
            if has_description:
                value["description"] = desc or getattr(page, "summary", "")

            content_type_label = get_content_type_for_page(page)
            page_release_date = page.publication_date

        if not value:
            return None

        if content_type := self.get("content_type"):
            content_type_label = get_related_content_type_label(content_type)

        release_date: date | datetime | None = self.get("release_date") or page_release_date

        if content_type_label or release_date:
            value["metadata"] = {}

        if content_type_label:
            value["metadata"] = {
                "object": {"text": content_type_label},
            }

        if release_date:
            value["metadata"]["date"] = get_document_metadata_date(release_date)

        return value

    def get_related_link(self, context: dict | None = None) -> dict[str, str | dict[str, str | dict[str, Any]]] | None:
        """Returns the required structure for the related link DS component.

        Ref: https://service-manual.ons.gov.uk/design-system/components/document-list
        """
        if link := self.get_link(context=context):
            related_link: dict[str, str | dict[str, str | dict[str, Any]]] = {
                "title": {"text": link["text"], "url": link["url"]},
            }
            if description := link.get("description", ""):
                related_link["description"] = description

            if metadata := link.get("metadata"):
                related_link["metadata"] = metadata

            return related_link
        return None

    @cached_property
    def link(self) -> dict | None:
        return self.get_link()


class LinkBlock(StructBlock):
    """Link block with page or link validation."""

    page = PageChooserBlock(required=False)
    external_url = URLBlock(required=False, label="or External Link")
    title = CharBlock(
        help_text="Populate when adding an external link. "
        "When choosing a page, you can leave it blank to use the page's own title",
        required=False,
    )

    class Meta:
        icon = "link"
        value_class = LinkBlockStructValue

    def clean(self, value: LinkBlockStructValue) -> LinkBlockStructValue:
        """Validate that either a page or external link is provided, and that external links have a title."""
        value = super().clean(value)
        page = value.get("page")
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
