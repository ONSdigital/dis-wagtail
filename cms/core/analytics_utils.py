from collections.abc import Iterable
from datetime import date, datetime
from typing import Any
from urllib.parse import urlparse


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


def get_gtm_attributes_file_download(
    *,
    text: str,
    url: str,
    file_extension: str,
    file_name: str,
    file_size_kb: str | None,
) -> dict[str, str]:
    """Gets GTM attributes for file download links."""
    parsed_url = urlparse(url)
    attributes = {
        "data-ga-event": "file-download",
        "data-ga-file-extension": file_extension,
        "data-ga-file-name": file_name,
        "data-ga-link-text": text,
        "data-ga-link-url": parsed_url.path,
    }

    if parsed_url.hostname is not None:
        attributes["data-ga-link-domain"] = parsed_url.hostname

    if file_size_kb is not None:
        attributes["data-ga-file-size"] = file_size_kb
    return attributes
