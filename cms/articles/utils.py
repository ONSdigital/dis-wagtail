from typing import TYPE_CHECKING

from django.utils.formats import date_format

if TYPE_CHECKING:
    from django_stubs_ext import StrPromise
    from wagtail.blocks.stream_block import StreamChild


def serialize_correction_or_notice(entry: "StreamChild", entry_type: "StrPromise") -> dict:
    """Serialize a correction or notice entry for the API."""
    return {
        "text": entry_type,
        "date": {
            "iso": date_format(entry.value["when"], "c"),
            "short": date_format(entry.value["when"], "DATE_FORMAT"),
        },
        "description": entry.value["text"],
    }
