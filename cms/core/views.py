from __future__ import annotations  # needed for unquoted forward references because of Django Views

import json
import logging
import platform
from http import HTTPStatus
from typing import TYPE_CHECKING

import redis
import redis.exceptions
from django.conf import settings
from django.core.cache import caches
from django.core.exceptions import PermissionDenied
from django.db import DatabaseError, connections
from django.http import Http404, HttpResponse, HttpResponseServerError, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views import View, defaults
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET
from django_redis import get_redis_connection
from django_redis.cache import RedisCache
from wagtail.admin.auth import user_has_any_page_permission, user_passes_test
from wagtail.models import Page, Revision

from cms.bundles.mixins import BundledPageMixin
from cms.bundles.permissions import get_bundle_permission, user_can_preview_bundle
from cms.core.utils import create_data_csv_download_response_from_data
from cms.workflows.utils import is_page_ready_to_preview

if TYPE_CHECKING:
    from django.http import HttpRequest

    from cms.users.models import User


logger = logging.getLogger(__name__)

DB_HEALTHCHECK_QUERY = "SELECT 1"


def page_not_found(
    request: HttpRequest, exception: Exception, template_name: str = "templates/pages/errors/404.html"
) -> HttpResponse:
    """Custom 404 error view to use our page not found template."""
    return defaults.page_not_found(request, exception, template_name)


def server_error(request: HttpRequest, template_name: str = "templates/pages/errors/500.html") -> HttpResponse:
    try:
        # Attempt to render the main, translatable 500 page.
        return render(request, template_name, status=500)
    except Exception as e:  # pylint: disable=broad-exception-caught
        # If any exception occurs, log it and fall back.
        logger.error("Error rendering the primary 500.html page: %s. Falling back to the basic version.", e)
        try:
            # Render a simple, dependency-free HTML file.
            return render(request, "templates/pages/errors/500_fallback.html", status=500)
        except Exception as final_e:  # pylint: disable=broad-exception-caught
            # As a last resort, if even the basic template fails, return a short, plain response.
            logger.critical("FATAL: Could not render the basic 500 page: %s", final_e)
            return HttpResponseServerError(
                "<h1>Server Error (500)</h1><p>Sorry, there’s a problem with the service.</p>", content_type="text/html"
            )


def csrf_failure(
    request: HttpRequest,
    reason: str = "",  # given by Django
    template_name: str = "templates/pages/errors/403.html",
) -> HttpResponse:
    """Custom CSRF failure error view that also logs the failure."""
    csrf_logger = logging.getLogger("django.security.csrf")
    csrf_logger.exception("CSRF Failure: %s", reason)

    return render(request, template_name, status=HTTPStatus.FORBIDDEN)


@never_cache
@require_GET
def ready(request: HttpRequest) -> HttpResponse:
    """Readiness probe endpoint.

    If this fails, requests will not be routed to the container.
    """
    return HttpResponse(status=200)


@never_cache
@require_GET
def liveness(request: HttpRequest) -> HttpResponse:
    """Liveness probe endpoint.

    If this fails, the container will be restarted.

    Unlike the health endpoint, this probe returns at the first sign of issue.
    """
    for connection in connections.all():
        try:
            with connection.cursor() as cursor:
                cursor.execute(DB_HEALTHCHECK_QUERY)
                result = cursor.fetchone()

            if result != (1,):
                return HttpResponseServerError(f"Database {connection.alias} returned unexpected result")
        except Exception:  # pylint: disable=broad-exception-caught
            logger.exception("Database %s reported an error", connection.alias)
            return HttpResponseServerError(f"Database {connection.alias} reported an error")

    if isinstance(caches["default"], RedisCache):
        try:
            get_redis_connection().ping()
        except Exception:  # pylint: disable=broad-exception-caught
            logger.exception("Unable to ping Redis")
            return HttpResponseServerError("Unable to ping Redis")

    return HttpResponse(status=200)


@never_cache
@require_GET
def health(request: HttpRequest) -> HttpResponse:
    now = timezone.now().replace(microsecond=0)

    def build_check(name: str, message: str, failed: bool) -> dict:
        return {
            "name": name,
            "status": "CRITICAL" if failed else "OK",
            "status_code": 500 if failed else 200,
            "message": message,
            "last_checked": now.isoformat(),
            "last_success": now.isoformat() if not failed else None,
            "last_failure": now.isoformat() if failed else None,
        }

    data = {
        "version": {
            "build_time": settings.BUILD_TIME.isoformat() if settings.BUILD_TIME else None,
            "git_commit": settings.GIT_COMMIT,
            "language": "python",
            "language_version": platform.python_version(),
            "version": settings.TAG,
        },
        "uptime": round((now - settings.START_TIME).total_seconds() * 1000),
        "start_time": settings.START_TIME.isoformat(),
    }
    checks = []

    for connection in connections.all():
        failed = False
        message = "Database is ok"
        try:
            with connection.cursor() as cursor:
                cursor.execute(DB_HEALTHCHECK_QUERY)
                result = cursor.fetchone()

            if result != (1,):
                failed = True
                message = "Backend returned unexpected result"
        except Exception as e:  # pylint: disable=broad-exception-caught
            failed = True
            if isinstance(e, DatabaseError):
                message = "Backend failed"
            else:
                logger.exception("Unexpected error connection to backend %s", connection.alias)
                message = "Unexpected error"

        checks.append(build_check(f"{connection.alias} database", message, failed))

    if isinstance(caches["default"], RedisCache):
        failed = False
        message = "Cache is ok"
        try:
            get_redis_connection().ping()
        except Exception as e:  # pylint: disable=broad-exception-caught
            failed = True
            if isinstance(e, redis.exceptions.ConnectionError):
                message = "Ping failed"
            else:
                logger.exception("Unexpected error connection to Redis")
                message = "Unexpected error"

        checks.append(build_check("cache", message, failed))

    checks_failed = any(check["status"] != "OK" for check in checks)

    data["status"] = "CRITICAL" if checks_failed else "OK"
    data["checks"] = checks

    return JsonResponse(data, status=500 if checks_failed else 200)


def user_can_access_csv_download(user: User) -> bool:
    """Check if user can access CSV downloads for charts and tables.

    Allows access for users with page permissions OR bundle view permission.

    Note that a user may still not be able to download a specific CSV
    if they lack permissions on the relevant page or bundle.
    """
    if user_has_any_page_permission(user):
        return True
    # Bundle viewers can also access CSV downloads
    return user.has_perm(get_bundle_permission("view"))


def get_revision_page_for_request(request: HttpRequest, page_id: int, revision_id: int) -> Page:
    """Get the page as it was at the specified revision.

    Args:
        request: The HTTP request.
        page_id: The ID of the page.
        revision_id: The ID of the revision.

    Returns:
        The page object at the specified revision.

    Raises:
        PermissionDenied: If user lacks edit/publish permissions on the page
            or bundle preview permissions.
        Http404: If the page or revision does not exist.
    """
    # Get the page and check permissions
    page = get_object_or_404(Page, id=page_id).specific

    # Check standard Wagtail page permissions
    perms = page.permissions_for_user(request.user)
    has_page_perms = perms.can_edit()

    # Check bundle preview permissions (only if page is bundled)
    has_bundle_preview = False
    if not has_page_perms and isinstance(page, BundledPageMixin) and is_page_ready_to_preview(page):
        has_bundle_preview = any(user_can_preview_bundle(request.user, bundle) for bundle in page.bundles.all())

    if not (has_page_perms or has_bundle_preview):
        raise PermissionDenied

    # Get the revision - use object_id to match the page
    # Revisions use object_id (as string) to reference the page
    revision = get_object_or_404(Revision.page_revisions, id=revision_id, object_id=str(page_id))

    # Get the page as it was at this revision
    return revision.as_object()


def get_csv_data_from_chart(revision_page: Page, chart_id: str) -> tuple[list[list[str | int | float]], str]:
    """Extract CSV data and title from chart.

    Args:
        revision_page: The page object containing the chart.
        chart_id: The unique block ID of the chart.

    Returns:
        A tuple of (data, title) where data is a 2D list for CSV export.

    Raises:
        Http404: If chart not found or data is malformed.
    """
    chart_data = revision_page.get_chart(chart_id)
    if not chart_data:
        raise Http404
    try:
        data = json.loads(chart_data["table"]["table_data"])["data"]
    except (KeyError, json.JSONDecodeError) as e:
        logger.warning(
            "Failed to parse chart data: %s",
            e,
            extra={"chart_id": chart_id, "page_id": revision_page.id, "page_slug": revision_page.slug},
        )
        raise Http404 from e
    return data, chart_data.get("title", "chart")


def get_csv_data_from_table(revision_page: Page, table_id: str) -> tuple[list[list[str | int | float]], str]:
    """Extract CSV data and title from table.

    Args:
        revision_page: The page object containing the table.
        table_id: The unique block ID of the table.

    Returns:
        A tuple of (data, title) where data is a 2D list for CSV export.

    Raises:
        Http404: If table not found or data extraction fails.
    """
    try:
        csv_data = revision_page.get_table_data_for_csv(table_id)
    except ValueError as e:
        logger.warning(
            "Failed to extract table data: %s",
            e,
            extra={"table_id": table_id, "page_id": revision_page.id, "page_slug": revision_page.slug},
        )
        raise Http404 from e
    table_data = revision_page.get_table(table_id)
    title = table_data.get("title") or table_data.get("caption") or "table"
    return csv_data, title


@method_decorator(user_passes_test(user_can_access_csv_download), name="dispatch")
class RevisionChartDownloadView(View):
    """Admin view to download chart data from a page revision.

    This allows downloading chart CSVs from draft/unpublished content during preview.
    Uses the same permission model as Wagtail's revision views.
    """

    def get(self, request: HttpRequest, page_id: int, revision_id: int, chart_id: str) -> HttpResponse:
        """Handle GET request for chart download.

        Args:
            request: The HTTP request.
            page_id: The page ID.
            revision_id: The revision ID.
            chart_id: The chart block ID.

        Returns:
            CSV file download response.

        Raises:
            Http404: If chart not found or data is invalid.
        """
        revision_page = get_revision_page_for_request(request, page_id, revision_id)
        csv_data, title = get_csv_data_from_chart(revision_page, chart_id)
        return create_data_csv_download_response_from_data(csv_data, title=title)


@method_decorator(user_passes_test(user_can_access_csv_download), name="dispatch")
class RevisionTableDownloadView(View):
    """Admin view to download table data from a page revision.

    This allows downloading table CSVs from draft/unpublished content during preview.
    Uses the same permission model as Wagtail's revision views.
    """

    def get(self, request: HttpRequest, page_id: int, revision_id: int, table_id: str) -> HttpResponse:
        """Handle GET request for table download.

        Args:
            request: The HTTP request.
            page_id: The page ID.
            revision_id: The revision ID.
            table_id: The table block ID.

        Returns:
            CSV file download response.

        Raises:
            Http404: If table not found or data extraction fails.
        """
        revision_page = get_revision_page_for_request(request, page_id, revision_id)
        csv_data, title = get_csv_data_from_table(revision_page, table_id)
        return create_data_csv_download_response_from_data(csv_data, title=title)
