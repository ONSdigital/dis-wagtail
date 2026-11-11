import logging
import os
from contextlib import suppress
from http import HTTPStatus
from typing import Any
from urllib.parse import urlsplit

from django.conf import settings
from django.contrib.messages import constants as message_constants
from django.http import HttpRequest, HttpResponse, HttpResponsePermanentRedirect
from django.shortcuts import resolve_url
from django.urls import NoReverseMatch, Resolver404, resolve, reverse
from django.utils import timezone
from django.utils.deprecation import MiddlewareMixin
from django.utils.html import escape
from django.utils.translation import gettext_lazy as _
from wagtail.admin.views.mixins import SpreadsheetExportMixin
from wagtail.log_actions import log

from cms.core.utils import redirect

NON_TRAILING_SLASH_METHODS = {"GET", "HEAD"}
CLOUDFLARE_CACHE_TAG_HEADER = "Cache-Tag"

security_logger = logging.getLogger("cms.security")
UNAUTHORIZED_ACCESS_EVENT = "unauthorized access attempt"
UNAUTHENTICATED_ACCESS_EVENT = "unauthenticated access attempt"
PROTECTIVE_MONITORING_CLASSIFICATION = "PROTECTIVE_MONITORING"
# Must match the message in wagtail.admin.auth.permission_denied
WAGTAIL_PERMISSION_DENIED_MESSAGE = _("Sorry, you do not have permission to access this area.")

SITE_HISTORY_VIEW_ACTION = "reports.site_history_view"
SITE_HISTORY_URL_NAMES = {
    "wagtailadmin_reports:site_history",
    "wagtailadmin_reports:site_history_results",
}


ALLOWED_REQUEST_PATHS = {
    settings.DJANGO_ADMIN_HOME_PATH,
    settings.WAGTAILADMIN_HOME_PATH,
    "/__debug__/",
}
UNAUTHORISED_ACCESS_EXEMPT_URL_NAMES = {
    "wagtailadmin_login",
    "wagtailadmin_password_reset",
    "wagtailadmin_logout",
    # Sent automatically by the edit page, including after logout or session expiry
    "wagtailadmin_editing_sessions:ping",
    "wagtailadmin_editing_sessions:release",
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


class SiteHistoryReadAuditMiddleware(MiddlewareMixin):
    """Records successful reads of the Site history report in the audit log,
    so that access to the audit log is itself auditable.
    """

    def process_response(self, request: HttpRequest, response: HttpResponse) -> HttpResponse:
        resolver_match = getattr(request, "resolver_match", None)
        if (
            request.method != "GET"
            or response.status_code != HTTPStatus.OK
            or resolver_match is None
            or resolver_match.view_name not in SITE_HISTORY_URL_NAMES
        ):
            return response

        user = getattr(request, "user", None)
        if user is None or not user.is_authenticated:
            return response

        # Mirrors how Wagtail decides whether to return a spreadsheet
        export_format = request.GET.get("export")
        if export_format not in SpreadsheetExportMixin.FORMATS:
            export_format = None

        # The report isn't tied to a single object, so the entry is logged against the reader.
        log(
            instance=user,
            action=SITE_HISTORY_VIEW_ACTION,
            user=user,
            data={
                "export": export_format,
                "results_only": resolver_match.view_name == "wagtailadmin_reports:site_history_results",
                "query": request.META.get("QUERY_STRING", ""),
            },
        )
        return response


class UnauthorizedAccessLoggingMiddleware(MiddlewareMixin):
    """Logs denied requests (401/403 and admin redirects to login) to stdout as protective monitoring events.

    These events are intentionally not stored in the database.
    """

    def process_request(self, request: HttpRequest) -> None:
        request.protective_monitoring_started_at = timezone.now()  # type: ignore[attr-defined]

    def process_response(self, request: HttpRequest, response: HttpResponse) -> HttpResponse:
        if not self._is_denied(request, response):
            return response
        user = getattr(request, "user", None)

        event_type = self._get_event_type(request)
        data = {
            "event_type": event_type,
            "user_agent": request.META.get("HTTP_USER_AGENT", ""),
        }
        extra: dict[str, Any] = {
            "classification": PROTECTIVE_MONITORING_CLASSIFICATION,
            "http": {
                "host": request.META.get("HTTP_HOST", request.META.get("SERVER_NAME", "")),
                "method": request.method,
                "path": request.path,
                "query": request.META.get("QUERY_STRING", ""),
                "scheme": request.scheme,
                "started_at": getattr(request, "protective_monitoring_started_at", timezone.now()),
                "status_code": response.status_code,
            },
        }
        try:
            extra["http"]["port"] = int(request.get_port())
        except TypeError, ValueError:
            pass
        if not settings.IS_EXTERNAL_ENV:
            if user is not None and user.is_authenticated:
                external_user_id = getattr(user, "external_user_id", None)
                extra["auth"] = {"identity": str(external_user_id or user.pk), "identity_type": "user"}
                data["internal_user_id"] = user.pk
                data["email"] = user.email
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

        admin_root = f"/{settings.WAGTAILADMIN_HOME_PATH.strip('/')}"
        if request.path != admin_root and not request.path.startswith(f"{admin_root}/"):
            return False

        location_path = urlsplit(response.get("Location", "")).path
        # Views using Django's @login_required redirect to LOGIN_URL rather than Wagtail's login
        login_paths = {
            urlsplit(settings.WAGTAILADMIN_LOGIN_URL).path,
            urlsplit(resolve_url(settings.LOGIN_URL)).path,
        }
        if location_path in login_paths:
            # Wagtail redirects to login both anonymous users and users without admin access.
            # The login and password reset URLs redirect to the external login when core login is disabled.
            with suppress(Resolver404):
                return resolve(request.path).view_name not in UNAUTHORISED_ACCESS_EXEMPT_URL_NAMES
            return True

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
