import os
from http import HTTPStatus

from django.conf import settings
from django.http import HttpRequest, HttpResponse, HttpResponsePermanentRedirect
from django.utils.deprecation import MiddlewareMixin

from cms.core.utils import redirect

NON_TRAILING_SLASH_METHODS = {"GET", "HEAD"}
CLOUDFLARE_CACHE_TAG_HEADER = "Cache-Tag"
DEFAULT_WAGTAIL_CLOUDFLARE_CACHE_TAG = "wagtail"

ALLOWED_REQUEST_PATHS = {
    settings.DJANGO_ADMIN_HOME_PATH,
    settings.WAGTAILADMIN_HOME_PATH,
    "/__debug__/",
}


class NonTrailingSlashRedirectMiddleware(MiddlewareMixin):
    """Redirects requests with a trailing slash to the non-trailing-slash equivalent."""

    def process_request(self, request: HttpRequest) -> HttpResponsePermanentRedirect | None:
        """Redirects requests with a trailing slash."""
        if request.method not in NON_TRAILING_SLASH_METHODS:
            return None

        # Ignore admin URLs and root URL
        if request.path.endswith("/") and request.path != "/" and not self.is_request_path_allowed(request.path):
            # Remove trailing slash to check for extension
            path_without_slash = request.path.rstrip("/")
            _, extension = os.path.splitext(path_without_slash)

            # Only redirect if there's no file extension
            if not extension:
                query = request.META.get("QUERY_STRING", "")
                if query:
                    path_without_slash = f"{path_without_slash}?{query}"

                url: HttpResponsePermanentRedirect = redirect(path_without_slash, permanent=True)  # type: ignore
                return url
        return None

    def is_request_path_allowed(self, path: str) -> bool:
        """Check if the request path is allowed to be redirected."""
        stripped_path = path.lstrip("/")
        return any(stripped_path.startswith(allowed_path.lstrip("/")) for allowed_path in ALLOWED_REQUEST_PATHS)


class CloudflareWagtailCacheTagMiddleware(MiddlewareMixin):
    """Adds a Cloudflare cache tag header to Wagtail server route responses."""

    # TODO check edge cases
    def _is_wagtail_route(self, request: HttpRequest) -> bool:
        """Return True when the request was resolved through a Wagtail server route."""
        resolver_match = getattr(request, "resolver_match", None)
        if not resolver_match:
            return False

        excluded_paths = {
            "/api/",
            "/v1/",
            "/wagtail/",
            "/admin/",
            "/__debug__/",
        }

        request_path = request.path.lower()
        if any(request_path.startswith(excluded) for excluded in excluded_paths):
            return False

        # Check if view is from wagtail package
        view_func = getattr(resolver_match, "func", None)
        view_module = getattr(view_func, "__module__", "")

        return view_module.startswith("wagtail.")

    def process_response(self, request: HttpRequest, response: HttpResponse) -> HttpResponse:
        """Add the Cloudflare cache tag header to the response."""
        # Only tag successful responses, not client or server errors
        if response.status_code >= HTTPStatus.BAD_REQUEST:
            return response

        if not self._is_wagtail_route(request):
            return response

        cache_tag = getattr(
            settings,
            "WAGTAIL_CLOUDFLARE_CACHE_TAG",
            DEFAULT_WAGTAIL_CLOUDFLARE_CACHE_TAG,
        )

        if not cache_tag:
            return response

        # TODO rework, ensure exact match of cache tag not substring, check logic is solid
        existing_tags = response.get(CLOUDFLARE_CACHE_TAG_HEADER, "")
        if cache_tag not in existing_tags.split(","):  # TODO resolve
            if existing_tags:
                response[CLOUDFLARE_CACHE_TAG_HEADER] = f"{existing_tags}, {cache_tag}"
            else:
                response[CLOUDFLARE_CACHE_TAG_HEADER] = cache_tag

        return response
