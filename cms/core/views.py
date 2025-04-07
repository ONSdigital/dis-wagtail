import logging
from http import HTTPStatus
from typing import TYPE_CHECKING

from django.core.cache import caches
from django.db import connections
from django.http import HttpResponse, HttpResponseServerError
from django.shortcuts import render
from django.views import defaults
from django_redis import get_redis_connection
from django_redis.cache import RedisCache

if TYPE_CHECKING:
    from django.http import HttpRequest


logger = logging.getLogger(__name__)


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


def ready(request: "HttpRequest") -> HttpResponse:
    """Readiness probe endpoint.

    If this fails, requests will not be routed to the container.
    """
    return HttpResponse(status=200)


def liveness(request: "HttpRequest") -> HttpResponse:
    """Liveness probe endpoint.

    If this fails, the container will be restarted.
    """
    for connection in connections.all():
        # If this endpoint is the first request Django runs,
        # it won't have a connection yet.
        connection.ensure_connection()

        if not connection.is_usable():
            return HttpResponseServerError(content=f"'{connection.alias}' database connection is not usable.")

    if isinstance(caches["default"], RedisCache):
        get_redis_connection().ping()

    return HttpResponse(status=200)
