from __future__ import annotations

import uuid
from typing import Any

from behave.runner import Context
from playwright.sync_api import Page

from cms.navigation.models import MainMenu
from cms.topics.models import TopicPage
from cms.topics.tests.factories import TopicPageFactory


# Footer menu creation helper functions
# The helper functions below are used to interact with the Wagtail admin interface for creating
# and editing navigation menus during functional tests.
# They allow us to insert new blocks, fill in column titles and links, and choose pages from the page chooser modal.
def insert_block(page: Page, nth: int = 0) -> None:
    """Inserts a new column block by clicking the 'Insert a block' button."""
    page.get_by_role("button", name="Insert a block").nth(nth).click()


def fill_column_title(page: Page, col_index: int, title: str) -> None:
    """Fills the 'Column title' field for a given column index."""
    page.locator(f"#columns-{col_index}-value-title").fill(title)


def fill_column_link(page: Page, col_index: int, link_index: int, external_url: str, link_title: str = "") -> None:
    """Fills the external URL and link title for a given link index inside a column block."""
    if link_index > 0:
        page.get_by_role("button", name="Add").nth(link_index).click()

    page.locator(f"#columns-{col_index}-value-links-{link_index}-value-external_url").click()
    page.locator(f"#columns-{col_index}-value-links-{link_index}-value-external_url").fill(external_url)
    if link_title:
        page.locator(f"#columns-{col_index}-value-links-{link_index}-value-title").click()
        page.locator(f"#columns-{col_index}-value-links-{link_index}-value-title").fill(link_title)


def choose_page_link(page: Page, page_name: str = "Home") -> None:
    """Clicks on 'Choose a page' and selects the specified page from the Wagtail page chooser."""
    page.get_by_role("button", name="Choose a page").click()
    page.get_by_role("link", name=page_name).click()


def generate_columns(context: Context, num_columns: int) -> None:
    for i in range(num_columns):
        insert_block(context.page, nth=i)
        fill_column_title(context.page, col_index=i, title=f"Link Column {i + 1}")
        fill_column_link(
            context.page,
            col_index=i,
            link_index=0,
            external_url=f"https://www.link-column-{i + 1}.com/",
            link_title=f"Link Title {i + 1}",
        )


class MainMenuStreamValueBuilder:
    """Builds StreamField values.
    Helper class to build StreamField values for main menu creation tests.

    This class provides methods to construct the nested data structures required for the highlights, sections,
    and columns of a main menu's StreamField. It includes validation to ensure that the required fields are
    provided according to the business rules.
    """

    def _new_id(self) -> str:
        return str(uuid.uuid4())

    # --------------------
    # Highlights (StreamField block)
    # --------------------
    # Rules:
    # - must provide page OR external_url (not both, not neither)
    # - if external_url provided -> title required
    # - description always required
    def highlight(
        self,
        *,
        page: Page | None = None,
        external_url: str | None = None,
        title: str = "",
        description: str,
    ) -> dict[str, Any]:
        if (page is None) == (external_url is None):
            raise ValueError("Highlight must have exactly one of 'page' or 'external_url'.")

        if external_url and not title.strip():
            raise ValueError("Highlight with external_url must include a non-empty title.")

        if not description.strip():
            raise ValueError("Highlight must include a non-empty description.")

        return {
            "type": "highlight",
            "id": self._new_id(),
            "value": {
                "page": page.pk if page else None,
                "external_url": external_url,
                "title": title,
                "description": description,
            },
        }

    # --------------------
    # Topic Links (ListBlock item value)
    # --------------------
    # Rules:
    # - must provide topic page OR external_url
    # - if external_url provided -> title required
    def topic_link_value(
        self,
        *,
        page: TopicPage | None = None,
        external_url: str | None = None,
        title: str = "",
    ) -> dict[str, Any]:
        if (page is None) == (external_url is None):
            raise ValueError("Topic item must have exactly one of 'page' or 'external_url'.")

        if external_url and not title.strip():
            raise ValueError("Topic item with external_url must include a non-empty title.")

        return {
            "page": page.pk if page else None,
            "external_url": external_url,
            "title": title,
        }

    # --------------------
    # Sections (ListBlock item value)
    # --------------------
    # Rules (for now):
    # - page excluded
    # - must have external_url AND title
    def section_value(
        self,
        *,
        external_url: str,
        title: str,
        links: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        if not external_url.strip():
            raise ValueError("Section must include a non-empty external_url.")

        if not title.strip():
            raise ValueError("Section must include a non-empty title.")

        return {
            "section_link": {
                "external_url": external_url,
                "title": title,
            },
            "links": links or [],
        }

    # --------------------
    # Column (StreamField block)
    # --------------------
    def column(
        self,
        *,
        sections: list[dict[str, Any]],
    ) -> dict[str, Any]:
        if not sections:
            raise ValueError("Column must contain at least one section.")

        return {
            "type": "column",
            "id": self._new_id(),
            "value": {
                "sections": sections,
            },
        }


class FooterMenuStreamValueBuilder:
    """Builds StreamField values for footer menu creation tests.

    This class provides methods to construct the nested data structures required
    for the columns and links of a footer menu's StreamField.
    """

    def link_value(
        self,
        *,
        page: Page | None = None,
        external_url: str | None = None,
        title: str = "",
    ) -> dict[str, Any]:
        if (page is None) == (external_url is None):
            raise ValueError("Link must have exactly one of 'page' or 'external_url'.")

        if external_url and not title.strip():
            raise ValueError("Link with external_url must include a non-empty title.")

        return {
            "page": page.pk if page else None,
            "external_url": external_url,
            "title": title,
        }

    def column(
        self,
        *,
        title: str,
        links: list[dict[str, Any]],
    ) -> dict[str, Any]:
        if not title.strip():
            raise ValueError("Column must include a non-empty title.")

        if not links:
            raise ValueError("Column must contain at least one link.")

        return {
            "type": "column",
            "value": {
                "title": title,
                "links": links,
            },
        }


class MainMenuFixtureBuilder:
    """Helper class to build and save MainMenu fixtures with populated StreamField values for testing purposes."""

    def __init__(self) -> None:
        self._builder = MainMenuStreamValueBuilder()

    def create_highlights(self, page: Page, locale_suffix: str = "") -> list[dict[str, Any]]:
        return [
            self._builder.highlight(
                page=page,
                title=f"Information page highlight {locale_suffix}",
                description=f"Internal highlight pointing to an information page. {locale_suffix}",
            ),
            self._builder.highlight(
                external_url=f"https://example.com/highlight-1{locale_suffix}",
                title=f"External highlight 1 {locale_suffix}",
                description=f"External highlight #1. {locale_suffix}",
            ),
            self._builder.highlight(
                external_url=f"https://example.com/highlight-2{locale_suffix}",
                title=f"External highlight 2 {locale_suffix}",
                description=f"External highlight #2. {locale_suffix}",
            ),
        ]

    def create_columns(self, locale_suffix: str = "") -> list[dict[str, Any]]:
        columns = []
        for col_idx in range(1, 4):
            sections = []
            for sec_idx in range(1, 4):
                topic_page = TopicPageFactory()

                links = [
                    self._builder.topic_link_value(
                        page=topic_page,
                        title=f"Topic page {col_idx}.{sec_idx} {locale_suffix}",
                    ),
                    self._builder.topic_link_value(
                        external_url=f"https://example.com/col-{col_idx}/sec-{sec_idx}/topic-external-1{locale_suffix}",
                        title=f"External topic {col_idx}.{sec_idx}.1 {locale_suffix}",
                    ),
                    self._builder.topic_link_value(
                        external_url=f"https://example.com/col-{col_idx}/sec-{sec_idx}/topic-external-2{locale_suffix}",
                        title=f"External topic {col_idx}.{sec_idx}.2 {locale_suffix}",
                    ),
                ]

                sections.append(
                    self._builder.section_value(
                        external_url=f"https://example.com/col-{col_idx}/section-{sec_idx}{locale_suffix}",
                        title=f"Section {col_idx}.{sec_idx} {locale_suffix}",
                        links=links,
                    )
                )

            columns.append(self._builder.column(sections=sections))

        return columns

    def populate_main_menu_stream_value(
        self, menu: MainMenu, page: Page, locale_suffix: str = ""
    ) -> tuple[list[dict], list[dict]]:
        highlights = self.create_highlights(page, locale_suffix)
        columns = self.create_columns(locale_suffix)

        menu.highlights = highlights
        menu.columns = columns
        menu.save()

        return highlights, columns
