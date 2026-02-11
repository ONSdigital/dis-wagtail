import logging
import time
import uuid
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from functools import cache
from typing import TYPE_CHECKING, Any, Literal, cast

from django.db import transaction
from django.urls import reverse
from django.utils.dateparse import parse_datetime
from django.utils.translation import gettext_lazy as _
from wagtail.coreutils import resolve_model_string
from wagtail.log_actions import log
from wagtail.models import Page, get_page_models

from cms.core.fields import StreamField
from cms.release_calendar.enums import ReleaseStatus
from cms.release_calendar.utils import get_translated_string

from .enums import ACTIVE_BUNDLE_STATUSES, BundleStatus
from .permissions import user_can_manage_bundles

logger = logging.getLogger(__name__)

# Translatable strings for release calendar content sections.
# These are extracted by makemessages and translated at runtime via get_translated_string.
_("Publications")
_("Quality and methodology")

if TYPE_CHECKING:
    from django.contrib.auth.models import AnonymousUser
    from django.db.models import Model

    from cms.users.models import User

    from .models import Bundle


@dataclass
class BundleAPIBundleMetadata:
    """BundleAPIBundleMetadata is the core dataclass that normalizes bundle metadata
    for comparison between CMS and Bundle API.

    It normalizes:
    - preview_teams: None -> [], sorted by id for consistent comparison
    - scheduled_at: datetime/string -> UTC ISO-8601 format (no microseconds)
    - bundle_type: Auto-set to SCHEDULED if scheduled_at present, else MANUAL
    - managed_by: Defaults to WAGTAIL

    This normalization ensures that equivalent bundle data from different sources
    (CMS Bundle, Bundle API JSON) can be reliably compared for sync decisions.
    """

    title: str | None = None
    bundle_type: Literal["MANUAL", "SCHEDULED"] | None = None
    state: str | None = None
    managed_by: Literal["WAGTAIL"] | None = None
    preview_teams: list[dict[Literal["id"], str]] | None = None
    scheduled_at: datetime | str | None = None

    def __post_init__(self) -> None:
        self.preview_teams = sorted(
            self.preview_teams or [],
            key=lambda team: team.get("id", ""),  # Ensure consistent ordering for equality checks
        )
        self.scheduled_at = _normalise_date(self.scheduled_at)
        if not self.bundle_type:
            self.bundle_type = "SCHEDULED" if self.scheduled_at else "MANUAL"

        if not self.managed_by:
            self.managed_by = "WAGTAIL"

    def as_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_bundle(cls, bundle: Bundle) -> BundleAPIBundleMetadata:
        """Return a BundleAPIBundleMetadata instance populated from a Bundle instance."""
        return cls(
            title=bundle.name,
            state=str(bundle.status),
            managed_by="WAGTAIL",
            preview_teams=_get_preview_teams_for_bundle(bundle),
            scheduled_at=bundle.scheduled_publication_date,
        )

    @classmethod
    def from_api_response(cls, api_response: dict[str, Any]) -> BundleAPIBundleMetadata:
        """Return a BundleAPIBundleMetadata instance populated from a Bundle API response."""
        return cls(
            title=api_response.get("title"),
            bundle_type=api_response.get("bundle_type"),
            state=api_response.get("state"),
            managed_by=api_response.get("managed_by"),
            preview_teams=api_response.get("preview_teams") or [],
            scheduled_at=api_response.get("scheduled_at"),
        )


@cache
def get_bundleable_page_types() -> list[type[Page]]:
    # using this rather than inline import to placate pyright complaining about cyclic imports
    module = __import__("cms.bundles.mixins", fromlist=["BundledPageMixin"])
    bundle_page_mixin_class = module.BundledPageMixin

    return [model for model in get_page_models() if issubclass(model, bundle_page_mixin_class)]


def get_pages_in_active_bundles() -> list[int]:
    # using this rather than inline import to placate pyright complaining about cyclic imports
    bundle_page_class = resolve_model_string("bundles.BundlePage")

    return list(
        bundle_page_class.objects.filter(parent__status__in=ACTIVE_BUNDLE_STATUSES).values_list("page", flat=True)
    )


def _create_content_dict_for_pages(
    pages: list[tuple[dict[str, Any], str]], language_code: str = "en"
) -> list[dict[str, Any]]:
    """Helper function to create content dictionary for article and methodology pages.

    Args:
        pages: A list of tuples containing serialized page data and page type names.
        language_code: The language code for translating section titles (e.g., 'en', 'cy').
    """
    article_pages: list[dict[str, Any]] = []
    methodology_pages: list[dict[str, Any]] = []
    content: list[dict[str, Any]] = []

    for serialized_page, page_type in pages:
        match page_type:
            case "StatisticalArticlePage":
                article_pages.append(serialized_page)
            case "MethodologyPage":
                methodology_pages.append(serialized_page)
    if article_pages:
        # NB: This string needs to match the one at the top of the file
        title = get_translated_string("Publications", language_code)
        content.append({"type": "release_content", "value": {"title": title, "links": article_pages}})
    if methodology_pages:
        # NB: This string needs to match the one at the top of the file
        title = get_translated_string("Quality and methodology", language_code)
        content.append({"type": "release_content", "value": {"title": title, "links": methodology_pages}})
    return content


def serialize_page(page: Page) -> dict[str, Any]:
    """Serializes a page to a dictionary."""
    return {
        "id": uuid.uuid4(),
        "type": "item",
        "value": {"page": page.pk, "title": "", "description": "", "external_url": ""},
    }


def serialize_preview_page(page: Page, bundle_id: int, is_previewable: bool) -> dict[str, Any]:
    specific_page = page.specific_deferred
    if workflow_state := specific_page.current_workflow_state:
        state = workflow_state.current_task_state.task.name
    else:
        state = "Draft"
    return {
        "id": uuid.uuid4(),
        "type": "item",
        "value": {
            "page": None,
            "title": f"{specific_page.title} ({state})",
            "description": getattr(specific_page, "summary", ""),
            "external_url": reverse("bundles:preview", args=[bundle_id, page.pk]) if is_previewable else "#",
        },
    }


def serialize_bundle_content_for_published_release_calendar_page(
    bundle: Bundle, language_code: str = "en"
) -> list[dict[str, Any]]:
    """Serializes the content of a bundle for a published release calendar page.

    Args:
        bundle: The bundle to serialize.
        language_code: The language code for translating section titles (e.g., 'en', 'cy').
    """
    all_bundled_pages = bundle.get_bundled_pages()
    # Create a list of tuples with serialized pages and their specific class names
    all_pages = [(serialize_page(page), page.specific_class.__name__) for page in all_bundled_pages]

    return _create_content_dict_for_pages(all_pages, language_code)


def serialize_bundle_content_for_preview_release_calendar_page(
    bundle: Bundle, previewing_user: User | AnonymousUser, language_code: str = "en"
) -> list[dict[str, Any]]:
    """Serializes the content of a bundle for a release calendar page.

    The pages will be serialized with additional information such as the workflow
    state and linked to the preview URL.

    Args:
        bundle: The bundle to serialize.
        previewing_user: The user previewing the bundle.
        language_code: The language code for translating section titles (e.g., 'en', 'cy').

    Returns:
        A list of dictionaries representing the serialized content of the bundle.
    """
    all_pages = []
    previewable_pages = []

    all_bundled_pages = bundle.get_bundled_pages()

    if user_can_manage_bundles(previewing_user):
        previewable_pages = all_bundled_pages
    else:
        # NB: Currently previewers can see all possible pages which get displayed
        # in the release calendar, but this could be restricted in the future.
        previewable_pages = bundle.get_pages_for_previewers()
    for page in all_bundled_pages:
        serialized_page = serialize_preview_page(page, bundle.pk, page in previewable_pages)
        all_pages.append((serialized_page, page.specific_class.__name__))

    return _create_content_dict_for_pages(all_pages, language_code)


def serialize_datasets_for_release_calendar_page(bundle: Bundle) -> list[dict[str, Any]]:
    """Serializes the datasets of a bundle for a release calendar page."""
    return [
        {"type": "dataset_lookup", "id": uuid.uuid4(), "value": dataset["dataset"]}
        for dataset in bundle.bundled_datasets.all().values("dataset")
    ]


def get_dataset_preview_key(dataset_id: str, edition_id: str, version_id: str) -> str:
    """Generates a unique preview key for a dataset based on its identifiers.

    Args:
        dataset_id (str): The unique identifier for the dataset.
        edition_id (str): The edition identifier for the dataset.
        version_id (str): The version identifier for the dataset.

    Returns:
        str: A unique preview key for the dataset.
    """
    return f"dataset-{dataset_id}-{edition_id}-{version_id}"


def get_preview_items_for_bundle(
    *,
    bundle: Bundle,
    current_id: int | str,
    pages_in_bundle: list[Page],
    bundle_contents: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Generates a list of preview items for the bundle.

    Args:
        bundle (Bundle): The bundle for which to generate preview items.
        current_id (int | str): The ID of the page or dataset key being currently previewed.
        pages_in_bundle (list[Page]): The list of pages in the bundle to be used for generating preview items.
        bundle_contents (dict[str, Any] | None): Optional bundle contents from API for including datasets.

    Returns:
        list[dict[str, Any]]: A list of dictionaries representing the preview items.
    """
    preview_items = [
        {
            "text": getattr(item, "display_title", item.title),
            "value": reverse("bundles:preview", args=[bundle.id, item.pk]),
            "selected": item.pk == current_id,
        }
        for item in pages_in_bundle
    ]

    if release_calendar_page := bundle.release_calendar_page:
        preview_items.insert(
            0,
            {
                "text": getattr(release_calendar_page, "display_title", release_calendar_page.title),
                "value": reverse("bundles:preview_release_calendar", args=[bundle.id]),
                "selected": False,
            },
        )

    # Add datasets to preview items if bundle_contents is provided
    for item in (bundle_contents or {}).get("items", []):
        if item.get("content_type") != "DATASET":
            continue

        metadata = item.get("metadata", {})
        dataset_id = metadata.get("dataset_id")
        edition_id = metadata.get("edition_id")
        version_id = metadata.get("version_id")

        if not all((dataset_id, edition_id, version_id)):
            continue

        title = metadata.get("title", "Untitled Dataset")
        dataset_key = get_dataset_preview_key(dataset_id, edition_id, version_id)
        preview_items.append(
            {
                "text": f"{title} ({edition_id.replace('-', ' ').title()} · v{version_id} · Dataset)",
                "value": reverse(
                    "bundles:preview_dataset",
                    args=[bundle.id, dataset_id, edition_id, version_id],
                ),
                "selected": dataset_key == current_id,
            }
        )

    return preview_items


def _get_preview_teams_for_bundle(bundle: Bundle) -> list[dict[Literal["id"], str]]:
    """Get formatted preview teams for a bundle for API usage."""
    team_identifiers = bundle.teams.values_list("team__identifier", flat=True)
    return [{"id": identifier} for identifier in team_identifiers]


def _normalise_date(value: str | datetime | None) -> str | None:
    """Return the datetime in UTC ISO-8601 format (no microseconds).
    If a string can't be parsed, it is returned unchanged.
    """
    if value is None:
        return None

    # Convert string > datetime where possible
    if isinstance(value, str):
        dt = parse_datetime(value)
        if dt is None:
            return value
    else:
        dt = value

    # Add timezone if missing
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)

    # Normalise to UTC and strip microseconds
    dt = dt.astimezone(UTC).replace(microsecond=0)
    return dt.isoformat()


def get_page_title_with_workflow_status(page: Page) -> str:
    title: str = page.specific_deferred.get_admin_display_title()

    if workflow_state := page.current_workflow_state:
        return f"{title} ({workflow_state.current_task_state.task.name})"

    return f"{title} (Draft)"


def get_language_code_from_page(page: Page) -> str:
    """Get the language code from a page's locale for translation purposes.

    Normalizes 'en-gb' to 'en' for consistency with translation files.
    """
    language_code = page.locale.language_code
    return "en" if language_code == "en-gb" else language_code


def update_bundle_linked_release_calendar_page(bundle: Bundle) -> None:
    """Updates the release calendar page related to the bundle with the pages in the bundle."""
    page = bundle.release_calendar_page
    if page:  # To satisfy mypy, ensure page is not None
        language_code = get_language_code_from_page(page)
        content = serialize_bundle_content_for_published_release_calendar_page(bundle, language_code)
        datasets = serialize_datasets_for_release_calendar_page(bundle)

        page.content = cast(StreamField, content)
        page.datasets = cast(StreamField, datasets)
        page.status = ReleaseStatus.PUBLISHED
        revision = page.save_revision(log_action=True)
        revision.publish()


def publish_bundle(bundle: Bundle, *, update_status: bool = True) -> bool:
    """Publishes a given bundle.

    This means it publishes the related pages, as well as updates the linked release calendar.
    """
    # using this rather than inline import to placate pyright complaining about cyclic imports
    notifications = __import__(
        "cms.bundles.notifications.slack", fromlist=["notify_slack_of_publication_start", "notify_slack_of_publish_end"]
    )

    logger.info(
        "Publishing Bundle",
        extra={
            "bundle_id": bundle.pk,
            "event": "publishing_bundle",
        },
    )
    start_time = time.time()
    notifications.notify_slack_of_publication_start(bundle, url=bundle.full_inspect_url)

    pages_publish_successful = True

    for page in bundle.get_bundled_pages().specific(defer=True).select_related("latest_revision").not_live():
        try:
            # Durable ensures no other savepoint will roll back the publish
            with transaction.atomic(durable=True):
                if workflow_state := page.current_workflow_state:
                    # finish the workflow
                    workflow_state.current_task_state.approve()
                elif page.latest_revision:
                    # just run publish
                    page.latest_revision.publish(log_action="wagtail.publish.scheduled")
                else:
                    logger.error(
                        "Did not publish page as it is not in a workflow or has no revisions",
                        extra={
                            "bundle_id": bundle.pk,
                            "page_id": page.pk,
                            "event": "publish_page_failed",
                        },
                    )
        except Exception:  # pylint: disable=broad-exception-caught
            # Log exception, but don't raise it so publishing can continue
            logger.exception("Page publish failed", extra={"bundle_id": bundle.pk, "page_id": page.pk})
            pages_publish_successful = False

    if pages_publish_successful:
        # update the related release calendar and publish
        if bundle.release_calendar_page_id:
            update_bundle_linked_release_calendar_page(bundle)

        if update_status:
            bundle.status = BundleStatus.PUBLISHED
            bundle.save()

    publish_duration = time.time() - start_time

    if pages_publish_successful:
        logger.info(
            "Published bundle",
            extra={
                "bundle_id": bundle.pk,
                "duration": round(publish_duration * 1000, 3),
                "event": "published_bundle",
            },
        )
    else:
        logger.error(
            "Bundle publish failed",
            extra={
                "bundle_id": bundle.pk,
                "duration": round(publish_duration * 1000, 3),
                "event": "publish_failed",
            },
        )

    notifications.notify_slack_of_publish_end(
        bundle, publish_duration, url=bundle.full_inspect_url, successful=pages_publish_successful
    )

    if pages_publish_successful:
        log(action="wagtail.publish.scheduled", instance=bundle)

    return pages_publish_successful


def build_content_item_for_dataset(dataset: Any) -> dict[str, Any]:
    """Build a content item dict for a dataset following Bundle API swagger spec.

    Args:
        dataset: A Dataset instance with namespace, edition, and version fields

    Returns:
        A dictionary representing a ContentItem for the Bundle API
    """
    return {
        "content_type": "DATASET",
        "metadata": {
            "dataset_id": dataset.namespace,
            "edition_id": dataset.edition,
            "version_id": dataset.version,
        },
        "links": {
            "edit": get_data_admin_action_url("edit", dataset.namespace, dataset.edition, dataset.version),
            "preview": get_data_admin_action_url("preview", dataset.namespace, dataset.edition, dataset.version),
        },
    }


def extract_content_id_from_bundle_response(response: dict[str, Any], dataset: Any) -> str | None:
    """Extract content_id from Bundle API response for a specific dataset.

    Args:
        response: Bundle API response
        dataset: Dataset instance to find in the response

    Returns:
        The content_id if found, None otherwise
    """
    metadata = response.get("metadata", {})
    if (
        metadata.get("dataset_id") == dataset.namespace
        and metadata.get("edition_id") == dataset.edition
        and metadata.get("version_id") == dataset.version
    ):
        content_id = response.get("id")
        return content_id if content_id is not None else None

    return None


def get_data_admin_action_url(
    action: Literal["edit", "preview"], dataset_id: str, edition_id: str, version_id: str
) -> str:
    """Generate a relative URL for dataset actions in the ONS Data Admin interface.

    This function constructs relative URLs for dataset operations in the ONS Data Admin
    system, which is used for editing and previewing datasets.

    Args:
        action: The action to perform ("edit", "preview")
        dataset_id: The unique identifier for the dataset
        edition_id: The edition identifier for the dataset
        version_id: The version identifier for the dataset

    Returns:
        A relative URL string for the specified dataset action

    Example:
        >>> get_data_admin_action_url("edit", "cpih", "time-series", "1")
        "/data-admin/series/cpih/editions/time-series/versions/1"
    """
    prefix = "data-admin/series" if action == "edit" else "datasets"
    return f"/{prefix}/{dataset_id}/editions/{edition_id}/versions/{version_id}"


def in_active_bundle(item: Model) -> bool:
    return getattr(item, "active_bundle", None) is not None


def in_bundle_ready_to_be_published(item: Model) -> bool:
    active_bundle: Bundle | None = getattr(item, "active_bundle", None)
    return active_bundle is not None and active_bundle.is_ready_to_be_published
