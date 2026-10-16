import logging
import os
from contextlib import suppress
from http import HTTPStatus
from typing import Any
from urllib.parse import urlsplit

from django.conf import settings
from django.contrib.messages import constants as message_constants
from django.http import HttpRequest, HttpResponse, HttpResponsePermanentRedirect
from django.urls import NoReverseMatch, reverse
from django.utils import timezone
from django.utils.deprecation import MiddlewareMixin
from django.utils.html import escape
from django.utils.translation import gettext_lazy as _

from cms.core.utils import redirect

NON_TRAILING_SLASH_METHODS = {"GET", "HEAD"}
CLOUDFLARE_CACHE_TAG_HEADER = "Cache-Tag"

security_logger = logging.getLogger("cms.security")
UNAUTHORIZED_ACCESS_EVENT = "unauthorized access attempt"
UNAUTHENTICATED_ACCESS_EVENT = "unauthenticated access attempt"
PROTECTIVE_MONITORING_CLASSIFICATION = "PROTECTIVE_MONITORING"
# Must match the message in wagtail.admin.auth.permission_denied
WAGTAIL_PERMISSION_DENIED_MESSAGE = _("Sorry, you do not have permission to access this area.")


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
    """Adds a Cloudflare cache tag header to responses."""

    @staticmethod
    def _parse_cache_tags(header: str) -> list[str]:
        """Parse the Cache-Tag header into a list of tags."""
        return [tag.strip() for tag in header.split(",") if tag.strip()] if header else []

    def process_response(self, request: HttpRequest, response: HttpResponse) -> HttpResponse:
        """Add the Cloudflare cache tag header to the response."""
        cache_tag = settings.CMS_CLOUDFLARE_CACHE_TAG
        if not cache_tag:
            return response

        # Append the configured tag when missing, or create the header if absent.
        existing_header = response.get(CLOUDFLARE_CACHE_TAG_HEADER, "")
        existing_tags = self._parse_cache_tags(existing_header)
        if cache_tag not in existing_tags:
            updated_tags = [*existing_tags, cache_tag]
            response[CLOUDFLARE_CACHE_TAG_HEADER] = ",".join(updated_tags)

        return response


class UnauthorizedAccessLoggingMiddleware(MiddlewareMixin):
    """Logs denied requests (401/403 and admin redirects to login) to stdout as protective monitoring events.

    These events are intentionally not stored in the database.
    """

    def process_request(self, request: HttpRequest) -> None:
        request.protective_monitoring_started_at = timezone.now()  # type: ignore[attr-defined]

    def process_response(self, request: HttpRequest, response: HttpResponse) -> HttpResponse:
        if self._is_denied(request, response):
            user = getattr(request, "user", None)

            event_type = self._get_event_type(request)
            data = {
                "event_type": event_type,
                "user_agent": request.META.get("HTTP_USER_AGENT", ""),
            }
            extra: dict[str, Any] = {
                "classification": PROTECTIVE_MONITORING_CLASSIFICATION,
                "http": {
                    "host": request.META.get("SERVER_NAME", ""),
                    "method": request.method,
                    "path": request.path,
                    "port": int(request.get_port()),
                    "query": request.META.get("QUERY_STRING", ""),
                    "scheme": request.scheme,
                    "started_at": getattr(request, "protective_monitoring_started_at", timezone.now()),
                    "status_code": response.status_code,
                },
            }
            if user is not None and user.is_authenticated:
                extra["auth"] = {"identity": str(user.pk), "identity_type": "user"}
                data["email"] = user.email
            # Internal environments will share the IP address, so only log it
            # for external environments.
            if not settings.IS_EXTERNAL_ENV:
                data["ip_address"] = request.META.get("REMOTE_ADDR")

            security_logger.warning(event_type, extra={**extra, **data})
        return response

    @staticmethod
    def _get_event_type(request: HttpRequest) -> str:
        """Determines the event type based on whether the user is authenticated."""
        user = getattr(request, "user", None)
        if user is not None and user.is_authenticated:
            return UNAUTHORIZED_ACCESS_EVENT
        return UNAUTHENTICATED_ACCESS_EVENT

    @staticmethod
    def _is_denied(request: HttpRequest, response: HttpResponse) -> bool:
        if response.status_code in (HTTPStatus.UNAUTHORIZED, HTTPStatus.FORBIDDEN):
            return True

        if response.status_code != HTTPStatus.FOUND:
            return False

        admin_path = f"/{settings.WAGTAILADMIN_HOME_PATH.strip('/')}/"
        if not request.path.startswith(admin_path):
            return False

        location_path = urlsplit(response["Location"]).path
        if location_path == urlsplit(settings.WAGTAILADMIN_LOGIN_URL).path:
            # Wagtail redirects to login both anonymous users and users without admin access.
            # The login and password reset URLs redirect to the external login when core login is disabled.
            exempt_paths = set()
            for url_name in ("wagtailadmin_login", "wagtailadmin_password_reset"):
                with suppress(NoReverseMatch):
                    exempt_paths.add(reverse(url_name))
            return request.path not in exempt_paths

        return UnauthorizedAccessLoggingMiddleware._is_wagtail_permission_denied(request, location_path)

    @staticmethod
    def _is_wagtail_permission_denied(request: HttpRequest, location_path: str) -> bool:
        """Detects Wagtail's permission_denied redirect to the admin home, which sets an error message."""
        try:
            if location_path != reverse("wagtailadmin_home"):
                return False
        except NoReverseMatch:
            return False

        # Peek at the queued messages without consuming them.
        queued = getattr(getattr(request, "_messages", None), "_queued_messages", [])
        # Wagtail renders the message through a template, which escapes it and adds whitespace.
        denied_text = escape(str(WAGTAIL_PERMISSION_DENIED_MESSAGE))
        return any(
            message.level == message_constants.ERROR and denied_text in str(message.message) for message in queued
        )
