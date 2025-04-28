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
        "title": page.title,
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
    # If page.release_date_text is present, treat it as provisional_date
    if page.release_date_text:
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


def build_resource_dict(page: "Page") -> dict:
    """Single entry point that decides if we build standard or release payload.
    Returns a dict shaped according to the resource_metadata.yml spec.
    """
    base_data = build_standard_resource_dict(page)

    if page.search_index_content_type == "release":
        # If it's a release, update with release-specific fields
        release_data = build_release_specific_fields(page)
        base_data.update(release_data)

    return base_data


def get_model_by_name(model_name: str) -> type:
    for model in apps.get_models():
        if model.__name__ == model_name:
            return model
    raise LookupError(f"No model named '{model_name}' was found.")


def build_page_uri(page):
    """Build the URI for a given page based on its URL path."""
    path = page.url_path.strip("/").split("/", 1)[-1]
    return f"/{path}" if not getattr(settings, "WAGTAIL_APPEND_SLASH", True) else f"/{path}/"
