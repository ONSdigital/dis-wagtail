from typing import TYPE_CHECKING

from django.apps import apps
from django.conf import settings
from django.utils.encoding import force_str
from wagtail.coreutils import get_locales_display_names
from wagtail.rich_text import get_text_for_indexing

from cms.release_calendar.enums import ReleaseStatus

if TYPE_CHECKING:
    from wagtail.models import Page


def build_standard_resource_dict(page: "Page") -> dict:
    """Returns a dict with the standard resource fields.
    This covers the non-release case (and also forms the base of the release case).
    """
    return {
        "uri": build_page_uri(page),
        "content_type": page.search_index_content_type,
        "release_date": (page.release_date.isoformat() if getattr(page, "release_date", None) else None),
        "summary": get_text_for_indexing(force_str(page.summary)),
        "title": page.get_full_display_title() if hasattr(page, "get_full_display_title") else page.title,
        "topics": getattr(page, "topic_ids", []),
        "language": force_str(get_locales_display_names().get(page.locale_id)),
    }


def build_release_specific_fields(page: "Page") -> dict:
    """Builds the extra fields that only apply to release content_type."""
    data = {
        "finalised": page.status in [ReleaseStatus.CONFIRMED, ReleaseStatus.PROVISIONAL],
        "cancelled": page.status == ReleaseStatus.CANCELLED,
        "published": page.status == ReleaseStatus.PUBLISHED,
        "date_changes": [],
    }

    # If page.release_date_text is present, treat it as a provisional_date
    # and do not add release_date to the payload.
    if page.release_date_text:
        data["release_date"] = None
        data["provisional_date"] = page.release_date_text

    if getattr(page, "changes_to_release_date", None):
        data["date_changes"] = [
            {
                "change_notice": change.value.get("reason_for_change"),
                "previous_date": change.value.get("previous_date").isoformat(),
            }
            for change in page.changes_to_release_date
        ]

    return data


def build_resource_dict(page: "Page", old_url_path: str | None = None) -> dict:
    """Single entry point that decides if we build standard or release payload.
    Returns a dict shaped according to the resource_metadata.yml spec.
    old_url_path is optional, if provided it will be used to populate the uri_old field, which is used to remove
    old URIs from the search index.
    """
    base_data = build_standard_resource_dict(page)

    if page.search_index_content_type == "release":
        # If it's a release, update with release-specific fields
        release_data = build_release_specific_fields(page)
        base_data.update(release_data)

    if old_url_path:
        base_data["uri_old"] = build_uri_from_url_path(old_url_path)

    return base_data


def get_model_by_name(model_name: str) -> type:
    for model in apps.get_models():
        if model.__name__ == model_name:
            return model
    raise LookupError(f"No model named '{model_name}' was found.")


def build_page_uri(page: "Page") -> str:
    """Build the URI for a given page based on its URL path."""
    return build_uri_from_url_path(page.url_path)


def build_uri_from_url_path(url_path: str) -> str:
    """Build the URI for a given page url_path."""
    # The url_path includes the home page's "/home/" slug at the start, but our URLs don't, so we strip it out
    path = url_path.strip("/").split("/", 1)[-1]
    return f"/{path}" if not getattr(settings, "WAGTAIL_APPEND_SLASH", True) else f"/{path}/"
