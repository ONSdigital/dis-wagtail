from collections.abc import Sequence
from typing import TYPE_CHECKING, Any

from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.template.response import TemplateResponse
from django.urls import reverse
from django.views.generic import TemplateView
from wagtail.models import Page

from cms.bundles.models import Bundle
from cms.bundles.permissions import user_can_manage, user_can_preview

if TYPE_CHECKING:
    from django.http import HttpRequest


class PreviewBundleView(TemplateView):
    http_method_names: Sequence[str] = ["get"]

    def get(self, request: "HttpRequest", *args: Any, **kwargs: Any) -> TemplateResponse:
        bundle_id = kwargs["bundle_id"]
        bundle = get_object_or_404(Bundle, id=bundle_id)

        if not user_can_preview(request.user, bundle):
            raise PermissionDenied

        page_id = kwargs["page_id"]
        page = get_object_or_404(Page, id=page_id).get_latest_revision_as_object()

        if user_can_manage(self.request.user):
            pages_in_bundle = bundle.get_bundled_pages(specific=True)
        else:
            pages_in_bundle = bundle.get_pages_ready_for_review()

        if page not in pages_in_bundle:
            raise Http404

        # set the "preview" flags on the request
        request.is_dummy = True  # type: ignore[attr-defined]
        request.is_preview = True  # type: ignore[attr-defined]
        request.preview_mode = "bundle-preview"  # type: ignore[attr-defined]

        context = page.get_context(request)
        context["bundle_inspect_url"] = reverse("bundle:inspect", args=[bundle_id])
        context["preview_items"] = [
            {
                "text": getattr(item, "display_title", item.title),
                "value": reverse("bundles:preview", args=[bundle_id, item.pk]),
                "selected": item.pk == page_id,
            }
            for item in pages_in_bundle
        ]

        # TODO: log access
        return TemplateResponse(request, page.get_template(request), context)
