import logging
import time
import uuid
from functools import cache
from typing import TYPE_CHECKING, Any, cast

from django.urls import reverse
from wagtail.coreutils import resolve_model_string
from wagtail.log_actions import log
from wagtail.models import Page, get_page_models

from cms.bundles.enums import ACTIVE_BUNDLE_STATUSES, BundleStatus
from cms.bundles.permissions import user_can_manage_bundles
from cms.core.fields import StreamField
from cms.release_calendar.enums import ReleaseStatus

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from django.contrib.auth.models import AnonymousUser

    from cms.bundles.models import Bundle
    from cms.users.models import User


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


def _create_content_dict_for_pages(pages: list[tuple[dict[str, Any], str]]) -> list[dict[str, Any]]:
    """Helper function to create content dictionary for article and methodology pages."""
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
        content.append({"type": "release_content", "value": {"title": "Publications", "links": article_pages}})
    if methodology_pages:
        content.append({"type": "release_content", "value": {"title": "Methodology", "links": methodology_pages}})
    return content


def serialize_page(page: "Page") -> dict[str, Any]:
    """Serializes a page to a dictionary."""
    return {
        "id": uuid.uuid4(),
        "type": "item",
        "value": {"page": page.pk, "title": "", "description": "", "external_url": ""},
    }


def serialize_preview_page(page: "Page", bundle_id: int, is_previewable: bool) -> dict[str, Any]:
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


def serialize_bundle_content_for_published_release_calendar_page(bundle: "Bundle") -> list[dict[str, Any]]:
    """Serializes the content of a bundle for a published release calendar page."""
    all_bundled_pages = bundle.get_bundled_pages()
    # Create a list of tuples with serialized pages and their specific class names
    all_pages = [(serialize_page(page), page.specific_class.__name__) for page in all_bundled_pages]

    return _create_content_dict_for_pages(all_pages)


def serialize_bundle_content_for_preview_release_calendar_page(
    bundle: "Bundle", previewing_user: "User | AnonymousUser"
) -> list[dict[str, Any]]:
    """Serializes the content of a bundle for a release calendar page.

    The pages will be serialized with additional information such as the workflow
    state and linked to the preview URL.

    Args:
        bundle (Bundle): The bundle to serialize.
        previewing_user (User | AnonymousUser): The user previewing the bundle.

    Returns:
        list[dict[str, Any]]: A list of dictionaries representing the serialized content of the bundle.
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

    return _create_content_dict_for_pages(all_pages)


def serialize_datasets_for_release_calendar_page(bundle: "Bundle") -> list[dict[str, Any]]:
    """Serializes the datasets of a bundle for a release calendar page."""
    return [
        {"type": "dataset_lookup", "id": uuid.uuid4(), "value": dataset["dataset"]}
        for dataset in bundle.bundled_datasets.all().values("dataset")
    ]


def get_preview_items_for_bundle(bundle: "Bundle", page_id: int, pages_in_bundle: list[Page]) -> list[dict[str, Any]]:
    """Generates a list of preview items for the bundle.

    Args:
        bundle (Bundle): The bundle for which to generate preview items.
        page_id (int): The ID of the page being currently previewed.
        pages_in_bundle (list[Page]): The list of pages in the bundle to be used for generating preview items.

    Returns:
        list[dict[str, Any]]: A list of dictionaries representing the preview items.
    """
    preview_items = [
        {
            "text": getattr(item, "display_title", item.title),
            "value": reverse("bundles:preview", args=[bundle.id, item.pk]),
            "selected": item.pk == page_id,
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

    return preview_items


def get_page_title_with_workflow_status(page: Page) -> str:
    title: str = page.specific_deferred.get_admin_display_title()

    if workflow_state := page.current_workflow_state:
        return f"{title} ({workflow_state.current_task_state.task.name})"

    return f"{title} (Draft)"


def update_bundle_linked_release_calendar_page(bundle: "Bundle") -> None:
    """Updates the release calendar page related to the bundle with the pages in the bundle."""
    page = bundle.release_calendar_page
    if page:  # To satisfy mypy, ensure page is not None
        content = serialize_bundle_content_for_published_release_calendar_page(bundle)
        datasets = serialize_datasets_for_release_calendar_page(bundle)

        page.content = cast(StreamField, content)
        page.datasets = cast(StreamField, datasets)
        page.status = ReleaseStatus.PUBLISHED
        revision = page.save_revision(log_action=True)
        revision.publish()


def publish_bundle(bundle: "Bundle", *, update_status: bool = True) -> None:
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
    for page in bundle.get_bundled_pages().specific(defer=True).select_related("latest_revision"):
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

    # update the related release calendar and publish
    if bundle.release_calendar_page_id:
        update_bundle_linked_release_calendar_page(bundle)

    if update_status:
        bundle.status = BundleStatus.PUBLISHED
        bundle.save()
    publish_duration = time.time() - start_time
    logger.info(
        "Published bundle",
        extra={
            "bundle_id": bundle.pk,
            "duration": round(publish_duration * 1000, 3),
            "event": "published_bundle",
        },
    )

    notifications.notify_slack_of_publish_end(bundle, publish_duration, url=bundle.full_inspect_url)

    log(action="wagtail.publish.scheduled", instance=bundle)
