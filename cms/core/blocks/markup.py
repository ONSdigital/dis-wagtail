from typing import TYPE_CHECKING, Any

from django.conf import settings
from django.core.exceptions import ValidationError
from django.urls import reverse
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _
from wagtail import blocks
from wagtail.contrib.table_block.blocks import TableBlock as WagtailTableBlock
from wagtail_tinytableblock.blocks import TinyTableBlock

from cms.data_downloads.utils import flatten_table_data
from cms.datavis.blocks.utils import get_approximate_file_size_in_kb

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
        return [
            {
                "url": "#" + slugify(value),
                "text": value,
                "attributes": {
                    "data-ga-event": "navigation-onpage",
                    "data-ga-navigation-type": "table-of-contents",
                    "data-ga-section-title": value,
                },
            }
        ]


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
        label = "Basic table"

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
            raise ValidationError("Select an option for Table headers")

        data = value.get("data", [])
        all_cells_empty = all(not cell for row in data for cell in row)
        if all_cells_empty:
            raise ValidationError("The table cannot be empty")

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

    def render(self, value: dict, context: dict | None = None) -> str | SafeString:
        """The Wagtail core TableBlock has a very custom `render` method. We don't want that."""
        rendered: str | SafeString = super(blocks.FieldBlock, self).render(value, context)
        return rendered


class ONSTableBlock(TinyTableBlock):
    """The ONS table block."""

    source = blocks.CharBlock(label="Source", required=False)
    footnotes = blocks.RichTextBlock(label="Footnotes", features=settings.RICH_TEXT_BASIC, required=False)

    def __init__(
        self, *, local_blocks: list[blocks.Block] | None = None, search_index: bool = True, **kwargs: Any
    ) -> None:
        super().__init__(local_blocks=local_blocks, search_index=search_index, **kwargs)
        # relabeled to match the publishing team's terminology
        self.child_blocks["caption"].label = "Sub-heading"

    def _align_to_ons_classname(self, alignment: str) -> str:
        match alignment:
            case "right":
                return "ons-u-ta-right"
            case "left":
                return "ons-u-ta-left"
            case "center":
                return "ons-u-ta-center"
            case _:
                return ""

    def _prepare_cell(
        self, cell: dict[str, str | int], class_key: str, *, is_body_cell: bool = False
    ) -> dict[str, str | int]:
        """Prepare a single cell for the DS table macro."""
        cell_copy = dict(cell)
        if alignment := cell_copy.get("align"):
            cell_copy[class_key] = self._align_to_ons_classname(str(alignment))
            del cell_copy["align"]
        if is_body_cell and cell_copy.get("type") == "th":
            cell_copy["heading"] = True
        cell_copy.pop("type", None)
        if is_body_cell:
            cell_copy.pop("scope", None)
        return cell_copy

    def _prepare_header_cells(self, row: list[dict[str, str | int]]) -> list[dict[str, str | int]]:
        """Prepare header cells for the DS table macro."""
        return [self._prepare_cell(cell, "thClasses", is_body_cell=False) for cell in row]

    def _prepare_body_cells(self, row: list[dict[str, str | int]]) -> list[dict[str, str | int]]:
        """Prepare body cells for the DS table macro."""
        return [self._prepare_cell(cell, "tdClasses", is_body_cell=True) for cell in row]

    def get_context(self, value: dict, parent_context: dict | None = None) -> dict:
        """Insert the DS-ready options in the template context."""
        context: dict = super().get_context(value, parent_context=parent_context)

        data = value.get("data", {})

        if not data.get("rows") and not data.get("headers"):
            return context

        options = {
            "caption": value.get("caption"),
            "thList": [{"ths": self._prepare_header_cells(header_row)} for header_row in data.get("headers", [])],
            "trs": [{"tds": self._prepare_body_cells(row)} for row in data.get("rows", [])],
        }

        # Add download config if block_id and page context available
        block_id = context.get("block_id")
        if block_id and parent_context:
            options["download"] = self._get_download_config(
                value=value, parent_context=parent_context, block_id=block_id, data=data
            )

        table_context = {
            "title": value.get("title"),
            "options": options,
            "source": value.get("source"),
            "footnotes": value.get("footnotes"),
            **context,
        }

        return table_context

    def _get_download_config(self, *, value: dict, parent_context: dict, block_id: str, data: dict) -> dict[str, Any]:
        """Build download config for ONS Downloads component."""
        page = parent_context.get("page")
        if not page:
            return {}

        # Flatten table data for size calculation
        csv_rows = flatten_table_data(data)

        size_suffix = f" ({get_approximate_file_size_in_kb(csv_rows)})"

        # Build URL (preview vs published)
        request = parent_context.get("request")
        is_preview = getattr(request, "is_preview", False) if request else False
        csv_url = (
            self._build_preview_table_download_url(page, block_id, request)
            if is_preview
            else self._build_table_download_url(page, block_id, parent_context.get("superseded_version"))
        )

        return {
            "title": _("Download this table"),
            "itemsList": [{"text": f"{_('Download CSV')}{size_suffix}", "url": csv_url}],
        }

    @staticmethod
    def _build_table_download_url(page: Any, block_id: str, superseded_version: int | None = None) -> str:
        """Build table download URL for published pages."""
        base_url = page.url.rstrip("/")
        version_part = f"/versions/{superseded_version}" if superseded_version is not None else ""
        return f"{base_url}{version_part}/download-table/{block_id}"

    @staticmethod
    def _build_preview_table_download_url(page: Any, block_id: str, request: Any = None) -> str:
        """Build table download URL for preview mode."""
        revision_id = None
        if request and hasattr(request, "resolver_match") and request.resolver_match:
            revision_id = request.resolver_match.kwargs.get("revision_id")
        if revision_id is None and hasattr(page, "latest_revision_id"):
            revision_id = page.latest_revision_id
        if revision_id is None:
            return "#"

        return reverse(
            "data_downloads:revision_table_download",
            kwargs={"page_id": page.pk, "revision_id": revision_id, "table_id": block_id},
        )

    class Meta:
        icon = "table"
        template = "templates/components/streamfield/table_block.html"
