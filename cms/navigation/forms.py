from collections.abc import Callable, Iterable
from typing import TYPE_CHECKING

from django.core.exceptions import ValidationError
from django.forms.utils import ErrorList
from wagtail.admin.forms import WagtailAdminModelForm
from wagtail.blocks import StreamBlockValidationError, StructBlock, StructBlockValidationError, StructValue
from wagtail.models import Page

from cms.core.blocks.base import LinkBlockStructValue

if TYPE_CHECKING:
    from wagtail.blocks import StreamValue


def create_struct_error(field_name: str, message: str) -> StructBlockValidationError:
    """Create a StructBlockValidationError for a specific field with a single error message."""
    return StructBlockValidationError({field_name: ErrorList([ValidationError(message)])})


def check_duplicates(
    value: Page, seen_values: set, field_name: str, error_message: str
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


def collect_block_errors(
    items: Iterable[StructBlock], validator_function: Callable[[StructBlock, int], list[StructBlockValidationError]]
) -> dict[int, ErrorList]:
    """Apply a validator_function to each item in the list. If the validator returns errors,
    store them in a dictionary keyed by the item index.
    """
    errors_dict = {}

    for idx, item in enumerate(items):
        errors = validator_function(item, idx)
        if errors:
            errors_dict[idx] = ErrorList(errors)
    return errors_dict


def validate_links(
    link_value: LinkBlockStructValue, seen_pages: set[Page], seen_urls: set[str]
) -> list[StructBlockValidationError]:
    """Checks if link has been seen. Returns error if so."""
    errors = []

    link_page = link_value.get("page")
    link_url = link_value.get("external_url")

    if link_page is not None:
        errors += check_duplicates(link_page, seen_pages, "page", "Duplicate page. Please choose a different one.")
    if link_url is not None:
        errors += check_duplicates(link_url, seen_urls, "external_url", "Duplicate URL. Please add a different one.")
    return errors


class MainMenuAdminForm(WagtailAdminModelForm):
    """Custom form for the MainMenu model."""

    def clean_highlights(self) -> StreamValue:
        highlights = self.cleaned_data["highlights"]
        seen_pages: set[Page] = set()
        seen_urls: set[str] = set()

        def validate_highlight_block(
            block: LinkBlockStructValue,
            idx: int,  # pylint: disable=unused-argument
        ) -> list[StructBlockValidationError]:
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

    def clean_columns(self) -> StreamValue:
        columns_value = self.cleaned_data["columns"]
        seen_pages: set[Page] = set()
        seen_urls: set[str] = set()

        def validate_section(
            section_value: StructValue,
            idx: int,  # pylint: disable=unused-argument
        ) -> list[StructBlockValidationError]:
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

            def validate_sub_link_wrapper(
                link_data: LinkBlockStructValue,
                link_idx: int,  # pylint: disable=unused-argument
            ) -> list[StructBlockValidationError]:
                return validate_links(link_data, seen_pages, seen_urls)

            sub_links_block_errors = collect_block_errors(sub_links, validate_sub_link_wrapper)
            if sub_links_block_errors:
                sec_errors.append(
                    StructBlockValidationError(
                        {"links": ErrorList([StreamBlockValidationError(block_errors=sub_links_block_errors)])}
                    )
                )

            return sec_errors

        def validate_column_block(
            column_block: StructValue,
            col_idx: int,  # pylint: disable=unused-argument
        ) -> list[StructBlockValidationError]:
            """Validate a single column block, including its sections."""
            errors: list[StructBlockValidationError] = []
            column_value = column_block.value
            sections = column_value.get("sections", [])

            def validate_section_wrapper(sec_data: StructValue, sec_idx: int) -> list[StructBlockValidationError]:
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


class FooterMenuAdminForm(WagtailAdminModelForm):
    """Custom form for validating Footer Menu columns and links."""

    def clean_columns(self) -> StreamValue:
        """Validates the column fields to ensure no duplicate pages or urls."""
        columns_value = self.cleaned_data["columns"]
        seen_pages: set[Page] = set()
        seen_urls: set[str] = set()

        def validate_block_column(
            block_value: StructValue,
            idx: int,  # pylint: disable=unused-argument
        ) -> list[StructBlockValidationError]:
            """Validates each column block for duplicate links."""
            col_errors: list[StructBlockValidationError] = []
            column = block_value.value
            block_links = column.get("links", [])

            def validate_link_wrapper(
                link_data: LinkBlockStructValue,
                link_idx: int,  # pylint: disable=unused-argument
            ) -> list[StructBlockValidationError]:
                return validate_links(link_data, seen_pages, seen_urls)

            links_errors = collect_block_errors(block_links, validate_link_wrapper)
            if links_errors:
                col_errors.append(
                    StructBlockValidationError(
                        {"links": ErrorList([StreamBlockValidationError(block_errors=links_errors)])}
                    )
                )
            return col_errors

        block_errors = collect_block_errors(columns_value, validate_block_column)
        if block_errors:
            raise StreamBlockValidationError(block_errors=block_errors)
        return columns_value
