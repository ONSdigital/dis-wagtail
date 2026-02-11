from __future__ import annotations  # needed for unquoted forward references because of Django Views

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

    Readiness should reflect whether this instance can currently serve traffic,
    including access to required dependencies.
    """
    for connection in connections.all():
        try:
            with connection.cursor() as cursor:
                cursor.execute(DB_HEALTHCHECK_QUERY)
                result = cursor.fetchone()

            if result != (1,):
                return HttpResponseServerError(f"Database {connection.alias} returned unexpected result")
        except Exception:  # pylint: disable=broad-exception-caught
            logger.exception(
                "Database reported an error",
                extra={"connection_alias": connection.alias},
            )
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
def liveness(request: HttpRequest) -> HttpResponse:
    """Liveness probe endpoint.

    If this fails, the container will be restarted.

    This should be shallow and only indicate whether the process is alive and
    responsive; dependency issues (e.g. DB/Redis) belong in readiness.
    """
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
