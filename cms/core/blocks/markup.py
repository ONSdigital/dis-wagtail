from typing import TYPE_CHECKING, Any, Union

from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils.text import slugify
from django.utils.translation import gettext as _
from wagtail import blocks
from wagtail.contrib.table_block.blocks import TableBlock as WagtailTableBlock
from wagtail_tinytableblock.blocks import TinyTableBlock

if TYPE_CHECKING:
    from django.utils.safestring import SafeString


class HeadingBlock(blocks.CharBlock):
    """Section heading block."""

    class Meta:
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
        """Convert the value to the table of contents component macro format."""
        return [{"url": "#" + slugify(value), "text": value}]


class QuoteBlock(blocks.StructBlock):
    """The quote block."""

    quote = blocks.CharBlock(form_classname="title")
    attribution = blocks.CharBlock(required=False)

    class Meta:
        icon = "openquote"
        template = "templates/components/streamfield/quote_block.html"


class BasicTableBlock(WagtailTableBlock):
    """Provides a basic table block with data processed for Design System components."""

    class Meta:
        icon = "table"
        template = "templates/components/streamfield/basic_table_block.html"
        label = _("Basic table")

    def _get_header(self, value: dict) -> list[dict[str, str]]:
        """Prepares the table header for the Design System."""
        table_header = []
        if value.get("data", "") and len(value["data"]) > 0 and value.get("first_row_is_table_header", False):
            for cell in value["data"][0]:
                table_header.append({"value": cell or ""})
        return table_header

    def _get_rows(self, value: dict) -> list[dict[str, list[dict[str, str]]]]:
        """Prepares the table data rows for the Design System."""
        trs = []
        has_header = value.get("data", "") and len(value["data"]) > 0 and value.get("first_row_is_table_header", False)
        data = value["data"][1:] if has_header else value.get("data", [])

        for row in data:
            tds = [{"value": cell} for cell in row]
            trs.append({"tds": tds})

        return trs

    def clean(self, value: dict) -> dict:
        """Validate that a header was chosen, and the cells are not empty."""
        if not value or not value.get("table_header_choice"):
            raise ValidationError(_("Select an option for Table headers"))

        data = value.get("data", [])
        all_cells_empty = all(not cell for row in data for cell in row)
        if all_cells_empty:
            raise ValidationError(_("The table cannot be empty"))

        cleaned_value: dict = super().clean(value)
        return cleaned_value

    def get_context(self, value: dict, parent_context: dict | None = None) -> dict:
        """Insert the DS-ready options in the template context."""
        context: dict = super().get_context(value, parent_context=parent_context)

        return {
            "options": {
                "caption": value.get("table_caption"),
                "ths": self._get_header(value),
                "trs": self._get_rows(value),
            },
            **context,
        }

    def render(self, value: dict, context: dict | None = None) -> Union[str, "SafeString"]:
        """The Wagtail core TableBlock has a very custom `render` method. We don't want that."""
        rendered: str | SafeString = super(blocks.FieldBlock, self).render(value, context)
        return rendered


class ONSTableBlock(TinyTableBlock):
    """The ONS table block."""

    source = blocks.CharBlock(label=_("Source"), required=False)
    footnotes = blocks.RichTextBlock(label=_("Footnotes"), features=settings.RICH_TEXT_BASIC, required=False)

    def get_context(self, value: dict, parent_context: dict | None = None) -> dict:
        """Insert the DS-ready options in the template context."""
        context: dict = super().get_context(value, parent_context=parent_context)

        data = value.get("data", {})

        if not data["rows"] and not data["headers"]:
            return context

        return {
            "title": value.get("title"),
            "options": {
                "caption": value.get("caption"),
                "headers": data.get("headers", []),
                "trs": [{"tds": row} for row in data.get("rows", [])],
            },
            "source": value.get("source"),
            "footnotes": value.get("footnotes"),
            **context,
        }

    class Meta:
        icon = "table"
        template = "templates/components/streamfield/table_block.html"
