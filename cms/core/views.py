import logging
from http import HTTPStatus
from typing import TYPE_CHECKING, Any

from django.conf import settings
from django.contrib import messages
from django.http import HttpResponse
from django.shortcuts import render
from django.utils.decorators import method_decorator
from django.views import defaults
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect
from wagtail.admin.views.account import LogoutView

if TYPE_CHECKING:
    from django.http import HttpRequest


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
    """Readiness probe endpoint."""
    return HttpResponse(status=204)


class ONSLogoutView(LogoutView):
    """Log out the user from Wagtail and delete the auth cookies."""

    next_page = None

    @method_decorator(csrf_protect)
    @method_decorator(never_cache)
    def dispatch(self, request: "HttpRequest", *args: Any, **kwargs: Any) -> "HttpResponse":
        response: HttpResponse = super().dispatch(request, *args, **kwargs)

        # HACK: Clear the messages from the request
        list(messages.get_messages(request))

        # Delete auth cookies
        response.delete_cookie(settings.ACCESS_TOKEN_COOKIE_NAME)
        response.delete_cookie(settings.ID_TOKEN_COOKIE_NAME)
        response.delete_cookie(settings.REFRESH_TOKEN_COOKIE_NAME)

        return response
