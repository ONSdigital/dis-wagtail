from collections.abc import Iterable
from datetime import date, datetime
from typing import Any


def format_date_for_gtm(value: date | datetime) -> str:
    """Formats a date or datetime object to the Google Analytics date format (YYYYMMDD)."""
    return value.strftime("%Y%m%d")


def add_table_of_contents_gtm_attributes(items: Iterable[dict[str, Any]]) -> None:
    """Adds GTM attributes to each item in the table of contents."""
    for item in items:
        item["attributes"] = {
            "data-ga-event": "navigation-onpage",
            "data-ga-navigation-type": "table-of-contents",
            "data-ga-section-title": item["text"],
        }


def bool_to_yes_no(value: bool) -> str:
    """Converts a boolean True or False value to 'yes' or 'no' respectively."""
    return "yes" if value else "no"
