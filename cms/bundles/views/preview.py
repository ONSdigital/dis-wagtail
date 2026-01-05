from collections.abc import Sequence
from typing import TYPE_CHECKING, Any, cast

from django.conf import settings
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect
from django.template.response import TemplateResponse
from django.urls import reverse
from django.views.generic import TemplateView
from wagtail.log_actions import log
from wagtail.models import Page

from cms.bundles.clients.api import BundleAPIClient
from cms.bundles.models import Bundle
from cms.bundles.permissions import user_can_manage_bundles, user_can_preview_bundle
from cms.bundles.utils import (
    get_dataset_preview_key,
    get_preview_items_for_bundle,
    serialize_bundle_content_for_preview_release_calendar_page,
    serialize_datasets_for_release_calendar_page,
)
from cms.core.fields import StreamField
from cms.release_calendar.enums import ReleaseStatus

if TYPE_CHECKING:
    from django.http import HttpRequest, HttpResponseRedirect


class BundleContentsMixin:
    """Mixin to fetch bundle contents: datasets from the API,
    and pages from the database.
    """

    def get_bundle_contents(self, bundle: Bundle) -> dict[str, Any]:
        """Initializes API client and fetches bundle contents."""
        if not settings.DIS_DATASETS_BUNDLE_API_ENABLED or not bundle.bundle_api_bundle_id:
            return {}
        cookie_name = settings.ACCESS_TOKEN_COOKIE_NAME
        access_token = self.request.COOKIES.get(cookie_name)  # type: ignore[attr-defined]
        client = BundleAPIClient(access_token=access_token)
        return client.get_bundle_contents(bundle.bundle_api_bundle_id)

    def get_pages_in_bundle(self, bundle: Bundle) -> list[Page]:
        """Fetches pages in the bundle based on user permissions."""
        pages: list[Page] = []
        if user_can_manage_bundles(self.request.user):  # type: ignore[attr-defined]
            pages = bundle.get_bundled_pages(specific=True)
        else:
            pages = bundle.get_pages_for_previewers()
        return pages


class PreviewBundlePageView(BundleContentsMixin, TemplateView):
    http_method_names: Sequence[str] = ["get"]

    def get(self, request: HttpRequest, *args: Any, **kwargs: Any) -> TemplateResponse:
        bundle_id = kwargs["bundle_id"]
        bundle = get_object_or_404(Bundle, id=bundle_id)

        page_id = kwargs["page_id"]
        page = get_object_or_404(Page, id=page_id).get_latest_revision_as_object()

        if not user_can_preview_bundle(request.user, bundle):
            log(
                action="bundles.preview.attempt",
                instance=bundle,
                data={"type": "page", "id": page_id, "title": getattr(page, "display_title", page.title)},
            )
            raise PermissionDenied

        pages_in_bundle = self.get_pages_in_bundle(bundle)

        if page not in pages_in_bundle:
            raise Http404

        # set the "preview" flags on the request
        request.is_dummy = True  # type: ignore[attr-defined]
        request.is_preview = True  # type: ignore[attr-defined]
        request.preview_mode = "bundle-preview"  # type: ignore[attr-defined]

        context = page.get_context(request)
        context["bundle_inspect_url"] = reverse("bundle:inspect", args=[bundle_id])

        # Fetch bundle contents to include datasets in preview items
        bundle_contents = self.get_bundle_contents(bundle)

        context["preview_items"] = get_preview_items_for_bundle(
            bundle=bundle, current_id=page_id, pages_in_bundle=pages_in_bundle, bundle_contents=bundle_contents
        )

        log(
            action="bundles.preview",
            instance=bundle,
            data={"type": "page", "id": page_id, "title": getattr(page, "display_title", page.title)},
        )

        return TemplateResponse(request, page.get_template(request), context)


class PreviewBundleReleaseCalendarView(BundleContentsMixin, TemplateView):
    http_method_names: Sequence[str] = ["get"]

    def get(self, request: HttpRequest, *args: Any, **kwargs: Any) -> TemplateResponse:
        bundle_id = kwargs["bundle_id"]
        bundle = get_object_or_404(Bundle, id=bundle_id)

        release_calendar_page = bundle.release_calendar_page

        if not release_calendar_page:
            raise Http404

        log_data_entry = {
            "type": "calendar",
            "id": release_calendar_page.id,
            "title": getattr(release_calendar_page, "display_title", release_calendar_page.title),
        }

        if not user_can_preview_bundle(request.user, bundle):
            log(
                action="bundles.preview.attempt",
                instance=bundle,
                data=log_data_entry,
            )
            raise PermissionDenied

        # Make adjustments to page for preview
        release_calendar_page.status = ReleaseStatus.PUBLISHED
        release_calendar_page.content = cast(
            StreamField, serialize_bundle_content_for_preview_release_calendar_page(bundle, self.request.user)
        )
        release_calendar_page.datasets = cast(StreamField, serialize_datasets_for_release_calendar_page(bundle))

        context = release_calendar_page.get_context(request)

        log(
            action="bundles.preview",
            instance=bundle,
            data=log_data_entry,
        )

        pages_in_bundle = self.get_pages_in_bundle(bundle)

        request.is_dummy = True  # type: ignore[attr-defined]
        request.is_preview = True  # type: ignore[attr-defined]
        request.preview_mode = "bundle-preview"  # type: ignore[attr-defined]

        context["bundle_inspect_url"] = reverse("bundle:inspect", args=[bundle_id])

        # Fetch bundle contents to include datasets in preview items
        bundle_contents = self.get_bundle_contents(bundle)

        context["preview_items"] = get_preview_items_for_bundle(
            bundle=bundle,
            current_id=release_calendar_page.id,
            pages_in_bundle=pages_in_bundle,
            bundle_contents=bundle_contents,
        )

        return TemplateResponse(request, release_calendar_page.get_template(request), context)


class PreviewBundleDatasetView(BundleContentsMixin, TemplateView):
    """View to preview a dataset within a bundle."""

    # We use a custom template with an iframe to display the dataset preview
    template_name = "templates/bundles/preview.html"
    http_method_names: Sequence[str] = ["get"]

    @staticmethod
    def find_dataset_preview_url(
        bundle_contents: dict[str, Any], dataset_id: str, edition_id: str, version_id: str
    ) -> str | None:
        """Find the preview URL for a specific dataset in the bundle contents.

        Args:
            bundle_contents: The bundle contents from the API
            dataset_id: The dataset identifier
            edition_id: The edition identifier
            version_id: The version identifier

        Returns:
            The preview URL if found, None otherwise
        """
        for item in bundle_contents.get("items", []):
            if item.get("content_type") != "DATASET":
                continue

            metadata = item.get("metadata", {})
            if (
                metadata.get("dataset_id") == dataset_id
                and metadata.get("edition_id") == edition_id
                and str(metadata.get("version_id")) == version_id
            ):
                return item.get("links", {}).get("preview", "") or None

        return None

    def get(self, request: HttpRequest, *args: Any, **kwargs: Any) -> TemplateResponse | HttpResponseRedirect:
        bundle_id = kwargs["bundle_id"]

        if settings.DIS_DATASETS_BUNDLE_API_ENABLED is False:
            messages.error(
                request,
                "The Datasets Bundle API is not enabled. Cannot preview dataset.",
            )
            return redirect("bundle:inspect", bundle_id)

        bundle = get_object_or_404(Bundle, pk=bundle_id)

        if not user_can_preview_bundle(request.user, bundle):
            raise PermissionDenied

        bundle_contents = self.get_bundle_contents(bundle)

        dataset_id = kwargs["dataset_id"]
        edition_id = kwargs["edition_id"]
        version_id = str(kwargs["version_id"])  # Convert to string for consistency with API

        # Find the specific dataset being previewed to get its preview URL
        iframe_url = self.find_dataset_preview_url(bundle_contents, dataset_id, edition_id, version_id)

        if not iframe_url:
            messages.error(
                request,
                f"Dataset {dataset_id} (Edition: {edition_id}, Ver: {version_id}) "
                "could not be found in this bundle or does not have a preview available.",
            )
            # Return to the bundle inspect page if we cannot show a preview of the dataset
            return redirect("bundle:inspect", bundle_id)

        # Build preview items for all pages and datasets in the bundle.
        # While the view is for previewing a dataset, we still want to show all
        # items in the preview list.
        pages_in_bundle = self.get_pages_in_bundle(bundle)

        # Create a unique identifier for this dataset to mark it as selected
        dataset_key = get_dataset_preview_key(dataset_id, edition_id, version_id)

        context = {
            "view": self,  # for TemplateView compatibility
            "bundle": bundle,
            "bundle_inspect_url": reverse("bundle:inspect", args=[bundle_id]),
            "preview_items": get_preview_items_for_bundle(
                bundle=bundle, current_id=dataset_key, pages_in_bundle=pages_in_bundle, bundle_contents=bundle_contents
            ),
            "iframe_url": iframe_url,  # Preview URL to load in the iframe
        }

        log(
            action="bundles.preview",
            instance=bundle,
            data={
                "type": "dataset",
                "dataset_id": dataset_id,
                "edition_id": edition_id,
                "version_id": version_id,
            },
        )

        return TemplateResponse(request, self.template_name, context)
