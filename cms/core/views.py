import logging
import platform
from http import HTTPStatus
from typing import TYPE_CHECKING

import redis
import redis.exceptions
from baipw.utils import authorize as basic_auth_authorize
from django.conf import settings
from django.core.cache import caches
from django.core.management import CommandError, call_command, get_commands
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


@never_cache
@require_GET
def ready(request: "HttpRequest") -> HttpResponse:
    """Readiness probe endpoint.

    If this fails, requests will not be routed to the container.
    """
    return HttpResponse(status=200)


@never_cache
@require_GET
def liveness(request: "HttpRequest") -> HttpResponse:
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
def health(request: "HttpRequest") -> HttpResponse:
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


@never_cache
@require_GET
def management_command(request: "HttpRequest", command_name: str) -> HttpResponse:
    # Validates basic auth, or raises an exception
    basic_auth_authorize(request, "cms", settings.MANAGEMENT_COMMANDS_URL_SECRET)

    try:
        get_commands()[command_name]
    except KeyError:
        logger.exception("Unknown command %r", command_name)
        return HttpResponse("Unknown command", status=404)

    try:
        call_command(command_name, skip_checks=True, no_color=True)
    except CommandError:
        logger.exception("Error executing management command %r", command_name)
        return HttpResponse("Command failed", status=400)

    return HttpResponse()
