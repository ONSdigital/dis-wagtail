from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from django.utils.deprecation import MiddlewareMixin
from wagtail.admin.auth import require_admin_access

from cms.custom_permission_policies.views import DocumentChooseView, ImageChooseView

if TYPE_CHECKING:
    from django.http import HttpRequest, HttpResponse

    from cms.custom_permission_policies.views import ParentIdentifyingChooserViewMixin


class PatchChooserURLsMiddleware(MiddlewareMixin):
    @classmethod
    def get_view_overrides(cls) -> dict[str, type["ParentIdentifyingChooserViewMixin"]]:
        """Return a mapping of 'view names' to be overridden to the views that
        should handle the responses.
        """
        overrides = {
            "wagtailimages_chooser:choose": ImageChooseView,
            "wagtaildocs_chooser:choose": DocumentChooseView,
        }
        return overrides

    def process_view(
        self,
        request: "HttpRequest",
        view_func: Any,  # pylint: disable=unused-argument
        view_args: list[Any],
        view_kwargs: dict[str, Any],
    ) -> "HttpResponse | None":
        """If the resolved url for the request matches one of the overrides,
        use the override view to handle the request.
        """
        overrides = self.get_view_overrides()
        if request.resolver_match:
            replacement_view_class = overrides.get(request.resolver_match.view_name)
            if replacement_view_class:
                view: Callable[..., HttpResponse] = require_admin_access(replacement_view_class.as_view())
                return view(request, *view_args, **view_kwargs)
        return None
