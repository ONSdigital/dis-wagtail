from __future__ import annotations

import uuid
from typing import Any

from behave.runner import Context
from playwright.sync_api import Page

from cms.topics.models import TopicPage


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
