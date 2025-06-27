from typing import TYPE_CHECKING

from django.utils.formats import date_format
from django.utils.translation import gettext_lazy as _

if TYPE_CHECKING:
    from wagtail.blocks.stream_block import StreamChild


def serialize_correction_or_notice(entry: "StreamChild", *, superseded_url: str | None = None) -> dict:
    """Serialize a correction or notice entry for the API.

    Args:
        entry (StreamChild): The stream child containing the correction or notice data.
        superseded_url (str | None): Optional URL to the superseded version of the article
            if this is a correction. If provided, the item will be labeled as a correction.

    Returns:
        dict: A dictionary containing the serialized data.
    """
    content = {
        "text": _("Correction") if superseded_url else _("Notice"),
        "date": {
            "iso": date_format(entry.value["when"], "c"),
            "short": date_format(entry.value["when"], "DATE_FORMAT"),
        },
        "description": entry.value["text"],
    }

    if superseded_url:
        content["url"] = superseded_url
        content["urlText"] = _("View superseded version")

    return content
