import logging
from http import HTTPStatus
from typing import TYPE_CHECKING

from django.shortcuts import render
from django.views import defaults

if TYPE_CHECKING:
    from django.http import HttpRequest, HttpResponse


def page_not_found(
    request: "HttpRequest", exception: Exception, template_name: str = "templates/pages/errors/404.html"
) -> "HttpResponse":
    """Custom 404 error view to use our page not found template."""
    return defaults.page_not_found(request, exception, template_name)


def server_error(request: "HttpRequest", template_name: str = "templates/pages/errors/500.html") -> "HttpResponse":
    """Custom 500 error view to use our error template."""
    return defaults.server_error(request, template_name)


def csrf_failure(
    request: "HttpRequest",
    reason: str = "",  # given by Django
    template_name: str = "templates/pages/errors/403.html",
) -> "HttpResponse":
    """Custom CSRF failure error view that also logs the failure."""
    csrf_logger = logging.getLogger("django.security.csrf")
    csrf_logger.exception("CSRF Failure: %s", reason)

    return render(request, template_name, status=HTTPStatus.FORBIDDEN)
