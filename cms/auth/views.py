import logging
from typing import Any

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect
from wagtail.admin.views.account import LogoutView

logger = logging.getLogger(__name__)


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
        logger.info("Session extended successfully for user", extra={"user_id": request.user.user_id})
        return JsonResponse({"status": "success", "message": "Session extended."})

    return JsonResponse({"status": "error", "message": "Invalid request method."}, status=405)
