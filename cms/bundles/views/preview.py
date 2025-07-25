from collections.abc import Sequence
from typing import TYPE_CHECKING, Any, cast

from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.template.response import TemplateResponse
from django.urls import reverse
from django.views.generic import TemplateView
from wagtail.log_actions import log
from wagtail.models import Page

from cms.bundles.models import Bundle
from cms.bundles.permissions import user_can_manage_bundles, user_can_preview_bundle
from cms.bundles.utils import (
    get_preview_items_for_bundle,
    serialize_bundle_content_for_preview_release_calendar_page,
    serialize_datasets_for_release_calendar_page,
)
from cms.core.fields import StreamField
from cms.release_calendar.enums import ReleaseStatus

if TYPE_CHECKING:
    from django.http import HttpRequest


class PreviewBundleView(TemplateView):
    http_method_names: Sequence[str] = ["get"]

    def get(self, request: "HttpRequest", *args: Any, **kwargs: Any) -> TemplateResponse:
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

        if user_can_manage_bundles(self.request.user):
            pages_in_bundle = bundle.get_bundled_pages(specific=True)
        else:
            pages_in_bundle = bundle.get_pages_for_previewers()

        if page not in pages_in_bundle:
            raise Http404

        # set the "preview" flags on the request
        request.is_dummy = True  # type: ignore[attr-defined]
        request.is_preview = True  # type: ignore[attr-defined]
        request.preview_mode = "bundle-preview"  # type: ignore[attr-defined]

        context = page.get_context(request)
        context["bundle_inspect_url"] = reverse("bundle:inspect", args=[bundle_id])
        context["preview_items"] = get_preview_items_for_bundle(bundle, page_id, pages_in_bundle)

        log(
            action="bundles.preview",
            instance=bundle,
            data={"type": "page", "id": page_id, "title": getattr(page, "display_title", page.title)},
        )

        return TemplateResponse(request, page.get_template(request), context)


class PreviewBundleReleaseCalendarView(TemplateView):
    http_method_names: Sequence[str] = ["get"]

    def get(self, request: "HttpRequest", *args: Any, **kwargs: Any) -> TemplateResponse:
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

        if user_can_manage_bundles(self.request.user):
            pages_in_bundle = bundle.get_bundled_pages(specific=True)
        else:
            pages_in_bundle = bundle.get_pages_for_previewers()

        request.is_dummy = True  # type: ignore[attr-defined]
        request.is_preview = True  # type: ignore[attr-defined]
        request.preview_mode = "bundle-preview"  # type: ignore[attr-defined]

        context["bundle_inspect_url"] = reverse("bundle:inspect", args=[bundle_id])
        context["preview_items"] = get_preview_items_for_bundle(bundle, release_calendar_page.id, pages_in_bundle)

        return TemplateResponse(request, release_calendar_page.get_template(request), context)
