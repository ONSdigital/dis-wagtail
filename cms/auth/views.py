import logging
from typing import Any, Protocol, cast
from urllib.parse import urlencode

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import redirect
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect
from wagtail.admin.views.account import LogoutView

logger = logging.getLogger(__name__)


class _HasExternalUserId(Protocol):
    external_user_id: str  # the single attribute we need for logging


class ONSLogoutView(LogoutView):
    """Logs out the user from Wagtail and removes authentication cookies.

    This view extends Wagtail's LogoutView by clearing any site messages
    and deleting AWS Cognito authentication cookies, if enabled.
    """

    # Setting next_page to None will redirect to the default logout URL configured by 'LOGOUT_REDIRECT_URL'.
    next_page = None

    def dispatch(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        response: HttpResponse = super().dispatch(request, *args, **kwargs)

        # Clear user messages. Converting to list ensures that the iterator is exhausted.
        list(messages.get_messages(request))

        # Delete authentication cookies if AWS Cognito is enabled.
        if settings.AWS_COGNITO_LOGIN_ENABLED:
            response.delete_cookie(settings.ACCESS_TOKEN_COOKIE_NAME)
            response.delete_cookie(settings.ID_TOKEN_COOKIE_NAME)

        return response


@csrf_protect
@never_cache
@login_required
def extend_session(request: HttpRequest) -> JsonResponse:
    """Extends the session by marking it as modified, which resets its expiry timer."""
    if request.method == "POST":
        request.session.modified = True  # Flag session as modified to update expiry
        logger.info(
            "Session extended successfully for user",
            extra={"external_user_id": cast(_HasExternalUserId, request.user).external_user_id},
        )
        return JsonResponse({"status": "success", "message": "Session extended."})

    return JsonResponse({"status": "error", "message": "Invalid request method."}, status=405)


def frontend_login_redirect(request: HttpRequest) -> HttpResponse:
    """Redirect Wagtail frontend private-page login requests to SSO."""
    next_url = request.GET.get("next", "")
    safe_next = "/"

    # Only allow local relative paths for post-login redirect targets.
    # Reject absolute/protocol-relative URLs.
    if (
        isinstance(next_url, str)
        and next_url.startswith("/")
        and url_has_allowed_host_and_scheme(
            next_url,
            allowed_hosts=None,
            require_https=False,
        )
    ):
        safe_next = next_url

    absolute_next = request.build_absolute_uri(safe_next)
    query = urlencode({"redirect": absolute_next})
    separator = "&" if "?" in settings.WAGTAILADMIN_LOGIN_URL else "?"
    return redirect(f"{settings.WAGTAILADMIN_LOGIN_URL}{separator}{query}")
