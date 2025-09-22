from collections.abc import Iterable
from datetime import date, datetime
from typing import TYPE_CHECKING, Any, Optional, TypedDict, Union, cast

from django.utils.formats import date_format
from django.utils.translation import gettext_lazy as _
from wagtail.models import Page

from cms.core.custom_date_format import ons_date_format

if TYPE_CHECKING:
    from django.http import HttpRequest
    from django_stubs_ext import StrOrPromise

    from cms.topics.utils import ArticleDict, ExternalArticleDict, InternalArticleDict, MethodologyDict


class DocumentListItem(TypedDict):
    title: dict[str, "StrOrPromise"]
    metadata: dict[str, Any]
    description: "StrOrPromise"


# Type alias for cleaner function signatures
PageDataCollection = Iterable[Union["ArticleDict", "MethodologyDict"]]


def format_as_document_list_item(
    title: str, url: str, content_type: "StrOrPromise", description: str
) -> DocumentListItem:
    """Formats an object as a list element to be used in the ONS DocumentList design system component."""
    return {
        "title": {"text": title, "url": url},
        "metadata": {"object": {"text": content_type}},
        "description": f"<p>{description}</p>",
    }


def _format_external_link(page_dict: "ExternalArticleDict") -> DocumentListItem:
    """Format external link dictionary into DocumentListItem."""
    return format_as_document_list_item(
        title=page_dict["title"],
        url=page_dict["url"],
        content_type=_("Article"),
        description=page_dict.get("description", ""),
    )


def _format_page_object(
    page: "Page", request: Optional["HttpRequest"] = None, custom_title: Optional[str] = None
) -> DocumentListItem:
    """Format page object into DocumentListItem."""
    page_datum: DocumentListItem = format_as_document_list_item(
        title=custom_title or getattr(page, "display_title", page.title),
        url=page.get_url(request=request),
        content_type=getattr(page, "label", _("Page")),
        description=getattr(page, "listing_summary", "") or getattr(page, "summary", ""),
    )

    if release_date := getattr(page, "release_date", None):
        page_datum["metadata"]["date"] = get_document_metadata_date(release_date)
    return page_datum


def get_formatted_pages_list(
    pages: PageDataCollection,
    request: Optional["HttpRequest"] = None,
) -> list[DocumentListItem]:
    """Returns a formatted list of page data for the documentList DS macro.

    See the search results section in https://service-manual.ons.gov.uk/design-system/components/document-list.
    """
    data = []

    for page in pages:
        # Check for external article (only ExternalArticleDict has is_external=True)
        if page.get("is_external"):
            datum = _format_external_link(cast("ExternalArticleDict", page))
        else:
            # If not external, must be internal (or invalid)
            if "internal_page" not in page:
                # This should not happen in production but is a safeguard for unexpected data types
                continue

            # Handle dict format with internal_page and optional title
            internal_dict = cast("InternalArticleDict", page)
            internal_page = internal_dict["internal_page"]  # Extract the actual Page object
            custom_title = cast(Optional[str], page.get("title") if "title" in page else None)
            datum = _format_page_object(internal_page, request, custom_title)

        data.append(datum)

    return data


def get_document_metadata_date(value: date | datetime, *, prefix: "StrOrPromise | None" = None) -> dict[str, Any]:
    """Returns a dictionary with formatted date information for the DS document component metadata."""
    return {
        "prefix": prefix or _("Released"),
        "showPrefix": True,
        "iso": date_format(value, "c"),
        "short": ons_date_format(value, "DATE_FORMAT"),
    }


def get_document_metadata(
    content_type: "StrOrPromise | None",
    date_value: date | datetime | None,
    *,
    prefix: "StrOrPromise | None" = None,
) -> dict[str, Any]:
    """Returns a dictionary with formatted metadata information for the DS document component."""
    metadata: dict[str, Any] = {}

    if content_type:
        metadata["object"] = {"text": content_type}

    if date_value:
        metadata["date"] = get_document_metadata_date(date_value, prefix=prefix)

    return metadata
