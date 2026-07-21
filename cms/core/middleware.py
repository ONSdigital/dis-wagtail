import os

from django.conf import settings
from django.http import HttpRequest, HttpResponse, HttpResponsePermanentRedirect
from django.utils.deprecation import MiddlewareMixin

from cms.core.utils import redirect

NON_TRAILING_SLASH_METHODS = {"GET", "HEAD"}
CLOUDFLARE_CACHE_TAG_HEADER = "Cache-Tag"

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

    def _parse_cache_tags(self, header: str) -> list[str]:
        """Parse the Cache-Tag header into a list of tags."""
        return [tag.strip() for tag in header.split(",") if tag.strip()] if header else []

    def process_response(self, request: HttpRequest, response: HttpResponse) -> HttpResponse:
        """Add the Cloudflare cache tag header to the response."""
        cache_tag = getattr(settings, "WAGTAIL_CLOUDFLARE_CACHE_TAG", None)
        if cache_tag is None:
            return response

        cache_tag = str(cache_tag).strip()
        if not cache_tag:
            return response

        # Add tag if header already exists and tag is not present
        existing_header = response.get(CLOUDFLARE_CACHE_TAG_HEADER, "")
        existing_tags = self._parse_cache_tags(existing_header)
        if cache_tag not in existing_tags:
            updated_tags = [*existing_tags, cache_tag]
            response[CLOUDFLARE_CACHE_TAG_HEADER] = ",".join(updated_tags)

        return response
