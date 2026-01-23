from typing import TYPE_CHECKING

from django.utils.translation import gettext_lazy as _

from cms.core.custom_date_format import ons_date_format

# Re-exports for backwards compatibility
from cms.core.utils import create_data_csv_download_response_from_data, sanitize_data_for_csv

__all__ = ["create_data_csv_download_response_from_data", "sanitize_data_for_csv", "serialize_correction_or_notice"]

if TYPE_CHECKING:
    from wagtail.blocks.stream_block import StreamChild


def serialize_correction_or_notice(entry: StreamChild, *, superseded_url: str | None = None) -> dict:
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
