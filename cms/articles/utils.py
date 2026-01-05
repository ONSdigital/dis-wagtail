import csv
from typing import TYPE_CHECKING

from django.http import HttpResponse
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _

from cms.core.custom_date_format import ons_date_format

if TYPE_CHECKING:
    from wagtail.blocks.stream_block import StreamChild


def serialize_correction_or_notice(entry: "StreamChild", *, superseded_url: str | None = None) -> dict:
    """Serialize a correction or notice entry for the Design System.

    Args:
        entry (StreamChild): The stream child containing the correction or notice data.
        superseded_url (str | None): Optional URL to the superseded version of the article
            if this is a correction. If provided, the item will be labeled as a correction.

    Returns:
        dict: A dictionary containing the serialized data.
    """
    is_correction = bool(superseded_url)
    content = {
        "text": _("Correction") if is_correction else _("Notice"),
        "date": {
            "iso": ons_date_format(entry.value["when"], "c"),
            "short": ons_date_format(entry.value["when"], "DATETIME_FORMAT" if is_correction else "DATE_FORMAT"),
        },
        "description": entry.value["text"],
    }

    if superseded_url:
        content["url"] = superseded_url
        content["urlText"] = _("View superseded version")

    return content


def create_data_csv_download_response_from_data(data: list[list[str | int | float]], *, title: str) -> HttpResponse:
    """Creates a Django HttpResponse for downloading a CSV file from table data.

    Args:
        data: The list of data rows to be converted to CSV, where each row is a list of values.
        title: The title for the CSV file, which will be slugified to create the filename.

    Returns:
        A Django HttpResponse object configured for CSV file download.
    """
    filename = slugify(title) or "chart"
    response = HttpResponse(
        content_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}.csv"',
        },
    )
    writer = csv.writer(response)
    writer.writerows(sanitize_data_for_csv(data))
    return response


def sanitize_data_for_csv(data: list[list[str | int | float]]) -> list[list[str | int | float]]:
    """Sanitize data for CSV export by escaping formula triggers.

    Prevents CSV injection by prepending ' to strings starting with
    =, +, -, @, or tab characters.
    """
    triggers = ("=", "+", "-", "@", "\t")

    return [
        [f"'{value}" if isinstance(value, str) and value.startswith(triggers) else value for value in row]
        for row in data
    ]
