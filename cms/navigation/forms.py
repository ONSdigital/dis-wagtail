from typing import TYPE_CHECKING

from django.core.exceptions import ValidationError
from django.forms.utils import ErrorList
from wagtail.admin.forms import WagtailAdminModelForm
from wagtail.blocks import StreamBlockValidationError, StructBlockValidationError

if TYPE_CHECKING:
    from wagtail.blocks import StreamValue


class MainMenuAdminForm(WagtailAdminModelForm):
    def clean_highlights(self) -> "StreamValue":
        highlights = self.cleaned_data["highlights"]
        # print(vars(highlights))
        # print("\n")

        block_errors = {}
        pages = set()
        external_urls = set()
        for idx, block in enumerate(highlights):
            if page := block.value["page"]:
                if page in pages:
                    block_errors[idx] = ErrorList(
                        [
                            StructBlockValidationError(
                                block_errors={
                                    "page": ErrorList(
                                        [ValidationError("Duplicate page. Please choose a different one.")]
                                    )
                                }
                            )
                        ]
                    )
                pages.add(page)

            elif external_url := block.value["external_url"]:
                if external_url in external_urls:
                    block_errors[idx] = ErrorList(
                        [
                            StructBlockValidationError(
                                block_errors={
                                    "external_url": ErrorList(
                                        [ValidationError("Duplicate URL. Please add a different one.")]
                                    )
                                }
                            )
                        ]
                    )
                external_urls.add(external_url)

        # print("Outputting highlights block errors")
        # print("Block errors", block_errors)
        # print("Pages", pages)
        # print("External URLs", external_urls)
        # print("\n")

        if block_errors:
            raise StreamBlockValidationError(block_errors=block_errors)

        return highlights

    def clean_columns(self) -> "StreamValue":
        """
        Validates duplicates across columns -> sections -> links,
        and raises block-level errors that appear inline in Wagtail.
        """
        columns_value = self.cleaned_data["columns"]

        # Track duplicates globally (or move these sets inside
        # the outer loop if you only want per-column uniqueness)
        seen_pages = set()
        seen_urls = set()

        # Top-level errors for the 'columns' StreamField,
        # keyed by index of the column block in the stream.
        # Each value must be an ErrorList of errors.
        columns_block_errors = {}

        for col_idx, column_block in enumerate(columns_value):
            # 'column_block.value' is a StructValue for your ColumnBlock:
            column_value = column_block.value
            sections = column_value.get("sections", [])

            # If this particular column has errors, we accumulate them in:
            # columns_block_errors[col_idx] = ErrorList([...])
            #
            # But because `sections` is itself a ListBlock, we must nest
            # a StructBlockValidationError that points to `sections`,
            # and inside that, a StreamBlockValidationError keyed by
            # section indices. So let's collect errors for each section:
            sections_block_errors = {}

            for sec_idx, section_value in enumerate(sections):
                # Each section_value is a StructValue from SectionBlock
                sec_errors = []  # A list of ValidationErrors or StructBlockValidationErrors

                # Check duplicates for the section_link
                section_link = section_value.get("section_link", {})
                section_page = section_link.get("page")
                section_url = section_link.get("external_url")

                if section_page:
                    if section_page in seen_pages:
                        sec_errors.append(
                            StructBlockValidationError(
                                {"section_link": ErrorList([ValidationError("Duplicate page in section link.")])}
                            )
                        )
                    else:
                        seen_pages.add(section_page)
                elif section_url:
                    if section_url in seen_urls:
                        sec_errors.append(
                            StructBlockValidationError(
                                {"section_link": ErrorList([ValidationError("Duplicate URL in section link.")])}
                            )
                        )
                    else:
                        seen_urls.add(section_url)

                # Now check sub‐links: section_value["links"] is a ListBlock
                sub_links = section_value.get("links", [])
                sub_links_block_errors = {}  # keyed by link_idx

                for link_idx, link_value in enumerate(sub_links):
                    # link_value is a StructValue (TopicLinkBlock or ThemeLinkBlock)
                    link_errors = []
                    link_page = link_value.get("page")
                    link_url = link_value.get("external_url")

                    if link_page:
                        if link_page in seen_pages:
                            link_errors.append(
                                StructBlockValidationError(
                                    {"page": ErrorList([ValidationError("Duplicate page in links.")])}
                                )
                            )
                        else:
                            seen_pages.add(link_page)
                    elif link_url:
                        if link_url in seen_urls:
                            link_errors.append(
                                StructBlockValidationError(
                                    {"external_url": ErrorList([ValidationError("Duplicate URL in links.")])}
                                )
                            )
                        else:
                            seen_urls.add(link_url)

                    # If this link has errors, store them under link_idx
                    if link_errors:
                        sub_links_block_errors[link_idx] = ErrorList(link_errors)

                # If we have any errors at the link level, nest them into
                # a StructBlockValidationError that points to the 'links' field.
                if sub_links_block_errors:
                    sec_errors.append(
                        StructBlockValidationError(
                            {"links": ErrorList([StreamBlockValidationError(block_errors=sub_links_block_errors)])}
                        )
                    )

                # If this section has any errors, attach them under sec_idx:
                if sec_errors:
                    # For sections, we collect them in a StreamBlockValidationError
                    # because sections is a ListBlock
                    sections_block_errors[sec_idx] = ErrorList(sec_errors)

            # If any sections had errors, we must attach them in a nested error
            if sections_block_errors:
                # The top-level block is "column" (a StructBlock),
                # so we attach an error for its 'sections' sub-field:
                columns_block_errors[col_idx] = ErrorList(
                    [
                        StructBlockValidationError(
                            {"sections": ErrorList([StreamBlockValidationError(block_errors=sections_block_errors)])}
                        )
                    ]
                )

        # Finally, if columns_block_errors is not empty,
        # we raise a StreamBlockValidationError so Wagtail
        # can map errors to each column index in the admin:
        if columns_block_errors:
            raise StreamBlockValidationError(block_errors=columns_block_errors)

        return columns_value
