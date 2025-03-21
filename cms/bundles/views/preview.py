from collections.abc import Sequence
from typing import TYPE_CHECKING, Any

from django.http import Http404
from django.shortcuts import get_object_or_404
from django.template.response import TemplateResponse
from django.urls import reverse
from django.views.generic import TemplateView
from wagtail.models import Page

from cms.bundles.models import Bundle

if TYPE_CHECKING:
    from django.http import HttpRequest


class PreviewBundleView(TemplateView):
    http_method_names: Sequence[str] = ["get"]

    def get(self, request: "HttpRequest", *args: Any, **kwargs: Any):
        bundle_id = kwargs["bundle_id"]
        bundle = get_object_or_404(Bundle, id=bundle_id)

        # TODO: check the current user can either edit the bundle, or is in team allowed in the bundle

        page_id = kwargs["page_id"]
        page = get_object_or_404(Page, id=page_id).get_latest_revision_as_object()

        pages_in_bundle = bundle.get_pages_ready_for_review()
        if page not in pages_in_bundle:
            raise Http404

        request.is_dummy = True
        request.is_preview = True
        request.preview_mode = "bundle-preview"

        context = page.get_context(request)
        context["bundle_inspect_url"] = reverse("bundle:inspect", args=[bundle_id])
        context["preview_items"] = [
            {
                "text": getattr(page, "display_title", page.title),
                "value": reverse("bundles:preview", args=[bundle_id, item.pk]),
                "selected": item.pk == page_id,
            }
            for item in pages_in_bundle
        ]

        # TODO: log access
        return TemplateResponse(request, page.get_template(request), context)
