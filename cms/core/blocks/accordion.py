from typing import Any

from django.conf import settings
from django.utils.translation import gettext_lazy as _
from wagtail import blocks


class AccordionSectionBlock(blocks.StructBlock):
    """A single accordion section with a title and content."""

    title = blocks.CharBlock(max_length=200, required=True, help_text="The title for this accordion section")
    content = blocks.RichTextBlock(
        features=settings.RICH_TEXT_BASIC, required=True, help_text="The content for this accordion section"
    )

    class Meta:
        icon = "doc-empty"
        label = "Accordion Section"


class AccordionBlock(blocks.ListBlock):
    """A container for multiple accordion sections."""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(AccordionSectionBlock, **kwargs)

    def get_context(self, value: Any, parent_context: dict[str, Any] | None = None) -> dict[str, Any]:
        """Generate context for the accordion template."""
        context: dict[str, Any] = super().get_context(value, parent_context=parent_context)
        accordion_sections = [
            {
                "title": section.get("title", ""),
                "content": section.get("content", ""),
            }
            for section in value
        ]

        context.update(
            {
                "accordion_sections": accordion_sections,
                "show_all_text": _("Show all"),
                "hide_all_text": _("Hide all"),
            }
        )

        return context

    class Meta:
        icon = "list-ul"
        label = "Accordion"
        template = "templates/components/streamfield/accordion_block.html"
