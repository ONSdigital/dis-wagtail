from typing import Any

from django.utils.text import slugify
from wagtail import blocks


class HeadingBlock(blocks.CharBlock):
    """Seection heading block."""

    class Meta:  # pylint: disable=missing-class-docstring,too-few-public-methods
        icon = "title"
        form_classname = "title"
        template = "templates/components/streamfield/heading_block.html"
        label = "Section heading"

    def __init__(self, **kwargs: Any) -> None:
        self.show_back_to_toc = kwargs.pop("show_back_to_toc", False)
        kwargs.setdefault("help_text", "This is output as level 2 heading (<code>h2</code>)")

        super().__init__(**kwargs)

    def get_context(self, value: Any, parent_context: dict[str, Any] | None = None) -> dict[str, Any]:
        context: dict[str, Any] = super().get_context(value, parent_context=parent_context)
        context["show_back_to_toc"] = self.show_back_to_toc

        return context

    def to_table_of_contents_items(self, value: Any) -> list[dict]:
        """Convert the value to the TOC macro format."""
        return [{"url": "#" + slugify(value), "text": value}]


class QuoteBlock(blocks.StructBlock):
    """The quote block."""

    quote = blocks.CharBlock(form_classname="title")
    attribution = blocks.CharBlock(required=False)

    class Meta:  # pylint: disable=missing-class-docstring,too-few-public-methods
        icon = "openquote"
        template = "templates/components/streamfield/quote_block.html"
