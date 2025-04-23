import logging
import platform
from http import HTTPStatus
from typing import TYPE_CHECKING

import redis
import redis.exceptions
from django.conf import settings
from django.core.cache import caches
from django.db import DatabaseError, connections
from django.http import HttpResponse, HttpResponseServerError, JsonResponse
from django.shortcuts import render
from django.utils import timezone
from django.views import defaults
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET
from django_redis import get_redis_connection
from django_redis.cache import RedisCache

if TYPE_CHECKING:
    from django.http import HttpRequest


logger = logging.getLogger(__name__)

DB_HEALTHCHECK_QUERY = "SELECT 1"


def page_not_found(
    request: "HttpRequest", exception: Exception, template_name: str = "templates/pages/errors/404.html"
) -> HttpResponse:
    """Custom 404 error view to use our page not found template."""
    return defaults.page_not_found(request, exception, template_name)


def server_error(request: "HttpRequest", template_name: str = "templates/pages/errors/500.html") -> HttpResponse:
    """Custom 500 error view to use our error template."""
    return defaults.server_error(request, template_name)


def csrf_failure(
    request: "HttpRequest",
    reason: str = "",  # given by Django
    template_name: str = "templates/pages/errors/403.html",
) -> HttpResponse:
    """Custom CSRF failure error view that also logs the failure."""
    csrf_logger = logging.getLogger("django.security.csrf")
    csrf_logger.exception("CSRF Failure: %s", reason)

    return render(request, template_name, status=HTTPStatus.FORBIDDEN)


@require_GET
def ready(request: "HttpRequest") -> HttpResponse:
    """Readiness probe endpoint.

    If this fails, requests will not be routed to the container.
    """
    return HttpResponse(status=200)


@require_GET
def liveness(request: "HttpRequest") -> HttpResponse:
    """Liveness probe endpoint.

    If this fails, the container will be restarted.
    """
    for connection in connections.all():
        try:
            with connection.cursor() as cursor:
                cursor.execute(DB_HEALTHCHECK_QUERY)
                result = cursor.fetchone()

            if result != (1,):
                return HttpResponseServerError(content=f"'{connection.alias}' database returned unexpected value.")
        except DatabaseError:
            return HttpResponseServerError(content=f"'{connection.alias}' database connection errored unexpectedly.")

    if isinstance(caches["default"], RedisCache):
        try:
            get_redis_connection().ping()
        except redis.exceptions.ConnectionError:
            return HttpResponseServerError(content="Failed to connect to cache.")

    return HttpResponse(status=200)


@never_cache
def health(request: "HttpRequest") -> HttpResponse:
    now = timezone.now().replace(microsecond=0)
    data = {
        "version": {
            "build_time": settings.BUILD_TIME,
            "git_commit": settings.GIT_COMMIT,
            "language": "python",
            "language_version": platform.python_version(),
            "version": settings.TAG,
        },
        "uptime": int((now - settings.START_TIME).total_seconds() * 1000),
        "start_time": settings.START_TIME.isoformat(),
    }
    checks = []

    for connection in connections.all():
        failed = False
        message = "Database is ok"
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                result = cursor.fetchone()

            if result != (1,):
                failed = True
                message = "Backend returned unexpected result"
        except DatabaseError:
            failed = True
            message = "Backend failed"

        checks.append(
            {
                "name": f"{connection.alias} database",
                "status": "CRITICAL" if failed else "OK",
                "status_code": 500 if failed else 200,
                "message": message,
                "last_checked": now.isoformat(),
                "last_success": now.isoformat() if not failed else None,
                "last_failure": now.isoformat() if failed else None,
            }
        )

    if isinstance(caches["default"], RedisCache):
        failed = False
        message = "Cache is ok"
        try:
            get_redis_connection().ping()
        except redis.exceptions.ConnectionError:
            failed = True
            message = "Ping failed"

        checks.append(
            {
                "name": "Cache",
                "status": "CRITICAL" if failed else "OK",
                "status_code": 500 if failed else 200,
                "message": message,
                "last_checked": now.isoformat(),
                "last_success": now.isoformat() if not failed else None,
                "last_failure": now.isoformat() if failed else None,
            }
        )

    checks_failed = any(check["status"] != "OK" for check in checks)

    data["status"] = "CRITICAL" if failed else "OK"
    data["checks"] = checks

    return JsonResponse(data, status=500 if checks_failed else 200)
