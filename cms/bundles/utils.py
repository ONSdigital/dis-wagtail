import uuid
from functools import cache
from typing import TYPE_CHECKING, Any

from django.urls import reverse
from wagtail.coreutils import resolve_model_string
from wagtail.models import Page, get_page_models

from cms.bundles.enums import ACTIVE_BUNDLE_STATUSES
from cms.bundles.permissions import user_can_manage_bundles

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
        state = "not in a workflow"
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


def serialize_bundle_content_for_release_calendar_page(
    bundle: "Bundle", previewing_user: "User | AnonymousUser | None" = None
) -> list[dict[str, Any]]:
    """Serializes the content of a bundle for a release calendar page."""
    content = []
    article_pages = []
    methodology_pages = []
    previewable_pages = []

    all_bundled_pages = bundle.get_bundled_pages()

    if previewing_user:
        if user_can_manage_bundles(previewing_user):
            previewable_pages = all_bundled_pages
        else:
            previewable_pages = bundle.get_pages_for_previewers()
    for page in all_bundled_pages:
        if previewing_user:
            serialized_page = serialize_preview_page(page, bundle.pk, page in previewable_pages)
        else:
            serialized_page = serialize_page(page)
        match page.specific_class.__name__:
            case "StatisticalArticlePage":
                article_pages.append(serialized_page)
            case "MethodologyPage":
                methodology_pages.append(serialized_page)

    if article_pages:
        content.append({"type": "release_content", "value": {"title": "Publications", "links": article_pages}})

    if methodology_pages:
        content.append({"type": "release_content", "value": {"title": "Methodology", "links": methodology_pages}})

    return content


def serialize_datasets_for_release_calendar_page(bundle: "Bundle") -> list[dict[str, Any]]:
    """Serializes the datasets of a bundle for a release calendar page."""
    return [
        {"type": "dataset_lookup", "id": uuid.uuid4(), "value": dataset["dataset"]}
        for dataset in bundle.bundled_datasets.all().values("dataset")
    ]
