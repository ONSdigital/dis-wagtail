from typing import TYPE_CHECKING, Any

from django.core.exceptions import ValidationError
from django.forms.utils import ErrorList
from wagtail.admin.forms import WagtailAdminModelForm
from wagtail.blocks import StreamBlockValidationError, StructBlockValidationError

if TYPE_CHECKING:
    from wagtail.blocks import StreamValue


def create_struct_error(field_name: str, message: str) -> StructBlockValidationError:
    """Create a StructBlockValidationError for a specific field with a single error message."""
    return StructBlockValidationError({field_name: ErrorList([ValidationError(message)])})


def check_duplicates(
    value: Any, seen_values: set, field_name: str, error_message: str
) -> list[StructBlockValidationError]:
    """Check if the given value has already been seen. If so, return a validation error.
    Otherwise, add it to the set of seen values.
    """
    errors = []
    if value:
        if value in seen_values:
            errors.append(create_struct_error(field_name, error_message))
        else:
            seen_values.add(value)
    return errors


def collect_block_errors(items: list[Any], validator_function) -> dict[int, ErrorList]:
    """Apply a validator_function to each item in the list. If the validator returns errors,
    store them in a dictionary keyed by the item index.
    """
    errors_dict = {}
    for idx, item in enumerate(items):
        errors = validator_function(item, idx)
        if errors:
            errors_dict[idx] = ErrorList(errors)
    return errors_dict


class MainMenuAdminForm(WagtailAdminModelForm):
    """Custom form for the MainMenu model."""

    def clean_highlights(self) -> "StreamValue":
        highlights = self.cleaned_data["highlights"]
        seen_pages = set()
        seen_urls = set()

        def validate_highlight_block(block: Any, idx: int) -> list[StructBlockValidationError]:
            """Validate an individual highlight block for duplicate page or external URL."""
            block_value = block.value
            page = block_value.get("page")
            external_url = block_value.get("external_url")

            errors = []
            errors += check_duplicates(page, seen_pages, "page", "Duplicate page. Please choose a different one.")
            errors += check_duplicates(
                external_url, seen_urls, "external_url", "Duplicate URL. Please add a different one."
            )
            return errors

        block_errors = collect_block_errors(highlights, validate_highlight_block)
        if block_errors:
            raise StreamBlockValidationError(block_errors=block_errors)

        return highlights

    def clean_columns(self) -> "StreamValue":
        columns_value = self.cleaned_data["columns"]
        seen_pages = set()
        seen_urls = set()

        def validate_sub_link(link_value: dict) -> list[StructBlockValidationError]:
            """Validate a single 'link' within a section (sub_link)."""
            errors = []
            link_page = link_value.get("page")
            link_url = link_value.get("external_url")

            errors += check_duplicates(link_page, seen_pages, "page", "Duplicate page. Please choose a different one.")
            errors += check_duplicates(
                link_url, seen_urls, "external_url", "Duplicate URL. Please add a different one."
            )
            return errors

        def validate_section(section_value: dict, idx: int) -> list[StructBlockValidationError]:
            """Validate a single 'section' within a column."""
            sec_errors: list[StructBlockValidationError] = []
            section_link = section_value.get("section_link", {})
            section_page = section_link.get("page")
            section_url = section_link.get("external_url")

            sec_errors += check_duplicates(
                section_page, seen_pages, "section_link", "Duplicate page. Please choose a different one."
            )
            sec_errors += check_duplicates(
                section_url, seen_urls, "section_link", "Duplicate URL. Please add a different one."
            )

            sub_links = section_value.get("links", [])

            def validate_sub_link_wrapper(link_data: Any, link_idx: int) -> list[StructBlockValidationError]:
                return validate_sub_link(link_data)

            sub_links_block_errors = collect_block_errors(sub_links, validate_sub_link_wrapper)
            if sub_links_block_errors:
                sec_errors.append(
                    StructBlockValidationError(
                        {"links": ErrorList([StreamBlockValidationError(block_errors=sub_links_block_errors)])}
                    )
                )

            return sec_errors

        def validate_column_block(column_block: Any, col_idx: int) -> list[StructBlockValidationError]:
            """Validate a single column block, including its sections."""
            errors: list[StructBlockValidationError] = []
            column_value = column_block.value
            sections = column_value.get("sections", [])

            def validate_section_wrapper(sec_data: Any, sec_idx: int) -> list[StructBlockValidationError]:
                return validate_section(sec_data, sec_idx)

            sections_block_errors = collect_block_errors(sections, validate_section_wrapper)
            if sections_block_errors:
                errors.append(
                    StructBlockValidationError(
                        {"sections": ErrorList([StreamBlockValidationError(block_errors=sections_block_errors)])}
                    )
                )
            return errors

        columns_block_errors = collect_block_errors(columns_value, validate_column_block)
        if columns_block_errors:
            raise StreamBlockValidationError(block_errors=columns_block_errors)

        return columns_value
