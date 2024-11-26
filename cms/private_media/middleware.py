from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from django.utils.deprecation import MiddlewareMixin
from wagtail.admin.auth import require_admin_access

from cms.private_media.views import document as document_views
from cms.private_media.views import image as image_views

if TYPE_CHECKING:
    from django.views import View
    from django.http import HttpRequest, HttpResponse


class PatchChooserURLsMiddleware(MiddlewareMixin):
    @classmethod
    def get_view_overrides(cls) -> dict[str, type[View]]:
        """Return a mapping of 'view names' to be overridden to the views that
        should handle the responses.
        """
        overrides = {
            "wagtailimages_chooser:choose": image_views.ImageChooseView,
            "wagtaildocs_chooser:choose": document_views.DocumentChooseView,
        }
        return overrides

    def process_view(self, request: "HttpRequest", view_func: Callable, view_args: list[Any], view_kwargs: dict[str, Any]) -> "HttpResponse | None":  # pylint: disable=unused-argument
        """If the resolved url for the request matches one of the overrides,
        use the override view to handle the request.
        """
        overrides = self.get_view_overrides()
        if request.resolver_match:
            replacement_view_class = overrides.get(request.resolver_match.view_name)
            if replacement_view_class:
                view: Callable[..., "HttpResponse"] = require_admin_access(replacement_view_class.as_view())
                return view(request, *view_args, **view_kwargs)
        return None
