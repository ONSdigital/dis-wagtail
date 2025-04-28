from typing import TYPE_CHECKING, Any, Optional, TypedDict

from django.conf import settings
from django.db.models import QuerySet
from django.utils.formats import date_format
from django.utils.translation import gettext_lazy as _

if TYPE_CHECKING:
    from django.http import HttpRequest
    from wagtail.models import Page


class DocumentListItem(TypedDict):
    title: dict[str, str]
    metadata: dict[str, Any]
    description: str


def get_formatted_pages_list(
    pages: list["Page"] | QuerySet["Page"], request: Optional["HttpRequest"] = None
) -> list[DocumentListItem]:
    """Returns a formatted list of page data for the documentList DS macro.

    See the search results section in https://service-manual.ons.gov.uk/design-system/components/document-list.
    """
    data = []
    for page in pages:
        datum: DocumentListItem = {
            "title": {
                "text": getattr(page, "display_title", page.title),
                "url": page.get_url(request=request),
            },
            "metadata": {
                "object": {"text": getattr(page, "label", _("Page"))},
            },
            "description": getattr(page, "listing_summary", "") or getattr(page, "summary", ""),
        }
        if release_date := page.release_date:
            datum["metadata"]["date"] = {
                "prefix": _("Released"),
                "showPrefix": True,
                "iso": date_format(release_date, "c"),
                "short": date_format(release_date, "DATE_FORMAT"),
            }
        data.append(datum)
    return data


def get_client_ip(request: "HttpRequest") -> str | None:
    """Get the IP address of the client.

    It's assumed this has been overridden by `django-xff`
    """
    if settings.IS_EXTERNAL_ENV:
        raise RuntimeError("Cannot get client IP in external environment.")
    return request.META.get("REMOTE_ADDR")
