from collections.abc import Iterable
from datetime import date, datetime
from typing import Any


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
