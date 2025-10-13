import os

from django.conf import settings
from django.http import HttpRequest, HttpResponsePermanentRedirect
from django.utils.deprecation import MiddlewareMixin

NON_TRAILING_SLASH_METHODS = {"GET", "HEAD"}

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
                return HttpResponsePermanentRedirect(path_without_slash)
        return None

    def is_request_path_allowed(self, path: str) -> bool:
        """Check if the request path is allowed to be redirected."""
        stripped_path = path.lstrip("/")
        return any(stripped_path.startswith(allowed_path.lstrip("/")) for allowed_path in ALLOWED_REQUEST_PATHS)
