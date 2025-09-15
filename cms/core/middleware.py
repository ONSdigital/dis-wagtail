import os

from django.conf import settings
from django.http import HttpRequest, HttpResponsePermanentRedirect
from django.utils.deprecation import MiddlewareMixin

NON_TRAILING_SLASH_METHODS = ["GET", "HEAD"]


class NonTrailingSlashRedirectMiddleware(MiddlewareMixin):
    """Redirects requests with a trailing slash to the non-trailing-slash equivalent."""

    def process_request(self, request: HttpRequest) -> HttpResponsePermanentRedirect | None:
        """Redirects requests with a trailing slash."""
        if request.method not in NON_TRAILING_SLASH_METHODS:
            return None

        # Ignore admin URLs and root URL
        if (
            request.path.endswith("/")
            and request.path != "/"
            and not request.path.lstrip("/").startswith(settings.DJANGO_ADMIN_HOME_PATH.lstrip("/"))
            and not request.path.lstrip("/").startswith(settings.WAGTAILADMIN_HOME_PATH.lstrip("/"))
        ):
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
