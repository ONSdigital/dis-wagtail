import logging
from typing import Any, Protocol, cast
from urllib.parse import urlencode, urlsplit

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import redirect
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
    next_url = request.GET.get("next", "/")

    # Only allow internal relative paths to be forwarded as redirect targets.
    # This prevents user-controlled absolute/protocol-relative URLs from reaching the redirect sink.
    if not isinstance(next_url, str) or not next_url.startswith("/") or next_url.startswith("//"):
        next_url = "/"
    else:
        parsed_next = urlsplit(next_url)
        if parsed_next.scheme or parsed_next.netloc:
            next_url = "/"

    absolute_next = request.build_absolute_uri(next_url)
    query = urlencode({"redirect": absolute_next})
    separator = "&" if "?" in settings.WAGTAILADMIN_LOGIN_URL else "?"

    return redirect(f"{settings.WAGTAILADMIN_LOGIN_URL}{separator}{query}")
