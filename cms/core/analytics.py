from collections.abc import Iterable
from datetime import date, datetime
from typing import Any

from cms.core.models import BasePage


def format_date_for_gtm(value: date | datetime) -> str:
    """Formats a date or datetime object to the Google Analytics date format (YYYYMMDD)."""
    return value.strftime("%Y%m%d")


def add_table_of_contents_gtm_attributes(items: Iterable[dict[str, Any]]) -> None:
    """Adds GTM attributes to each item in the table of contents."""
    for section_number, item in enumerate(items, 1):
        item["attributes"] = {
            "data-gtm-event": "table-of-contents-click",
            "data-gtm-interactionType": "table-of-contents",
            "data-gtm-label": item["text"],
            "data-gtm-section-number": section_number,
        }


def get_page_gtm_content_group(page: "BasePage") -> str | None:
    """Returns the GTM content group for a page, if it has one.
    This is the slug of the topic associated with the page, for a theme or topic page this will be it's own slug,
    otherwise it will be the slug of the parent topic page if it exists.
    """
    if str(type(page)) == "TopicPage" or str(type(page)) == "ThemePage":
        return page.slug

    for ancestor in page.get_ancestors():
        if str(type(ancestor)) == "TopicPage" or str(type(ancestor)) == "ThemePage":
            return ancestor.slug

    return None
