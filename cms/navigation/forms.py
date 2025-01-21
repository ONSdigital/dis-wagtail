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

        if block_errors:
            raise StreamBlockValidationError(block_errors=block_errors)

        return highlights

    def clean_columns(self) -> "StreamValue":
        columns_value = self.cleaned_data["columns"]

        seen_pages = set()
        seen_urls = set()

        columns_block_errors = {}

        for col_idx, column_block in enumerate(columns_value):
            column_value = column_block.value
            sections = column_value.get("sections", [])

            sections_block_errors = {}

            for sec_idx, section_value in enumerate(sections):
                sec_errors = []

                section_link = section_value.get("section_link", {})
                section_page = section_link.get("page")
                section_url = section_link.get("external_url")

                if section_page:
                    if section_page in seen_pages:
                        sec_errors.append(
                            StructBlockValidationError(
                                {
                                    "section_link": ErrorList(
                                        [ValidationError("Duplicate page. Please choose a different one.")]
                                    )
                                }
                            )
                        )
                    else:
                        seen_pages.add(section_page)
                elif section_url:
                    if section_url in seen_urls:
                        sec_errors.append(
                            StructBlockValidationError(
                                {
                                    "section_link": ErrorList(
                                        [ValidationError("Duplicate URL. Please add a different one.")]
                                    )
                                }
                            )
                        )
                    else:
                        seen_urls.add(section_url)

                sub_links = section_value.get("links", [])
                sub_links_block_errors = {}

                for link_idx, link_value in enumerate(sub_links):
                    link_errors = []
                    link_page = link_value.get("page")
                    link_url = link_value.get("external_url")

                    if link_page:
                        if link_page in seen_pages:
                            link_errors.append(
                                StructBlockValidationError(
                                    {
                                        "page": ErrorList(
                                            [ValidationError("Duplicate page. Please choose a different one.")]
                                        )
                                    }
                                )
                            )
                        else:
                            seen_pages.add(link_page)
                    elif link_url:
                        if link_url in seen_urls:
                            link_errors.append(
                                StructBlockValidationError(
                                    {
                                        "external_url": ErrorList(
                                            [ValidationError("Duplicate URL. Please add a different one.")]
                                        )
                                    }
                                )
                            )
                        else:
                            seen_urls.add(link_url)

                    if link_errors:
                        sub_links_block_errors[link_idx] = ErrorList(link_errors)

                if sub_links_block_errors:
                    sec_errors.append(
                        StructBlockValidationError(
                            {"links": ErrorList([StreamBlockValidationError(block_errors=sub_links_block_errors)])}
                        )
                    )

                if sec_errors:
                    sections_block_errors[sec_idx] = ErrorList(sec_errors)

            if sections_block_errors:
                columns_block_errors[col_idx] = ErrorList(
                    [
                        StructBlockValidationError(
                            {"sections": ErrorList([StreamBlockValidationError(block_errors=sections_block_errors)])}
                        )
                    ]
                )

        if columns_block_errors:
            raise StreamBlockValidationError(block_errors=columns_block_errors)

        return columns_value
