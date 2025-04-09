from typing import TYPE_CHECKING, Any

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect
from wagtail.admin.views.account import LogoutView

if TYPE_CHECKING:
    from django.http import HttpRequest


class ONSLogoutView(LogoutView):
    """Log out the user from Wagtail and delete the auth cookies."""

    next_page = None

    def dispatch(self, request: "HttpRequest", *args: Any, **kwargs: Any) -> "HttpResponse":
        response: HttpResponse = super().dispatch(request, *args, **kwargs)
        # Clear the messages from the request
        list(messages.get_messages(request))

        # Delete the auth cookies
        if settings.AWS_COGNITO_LOGIN_ENABLED:
            response.delete_cookie(settings.ACCESS_TOKEN_COOKIE_NAME)
            response.delete_cookie(settings.ID_TOKEN_COOKIE_NAME)

        return response


@csrf_protect
@never_cache
@login_required
def extend_session(request: "HttpRequest") -> JsonResponse:
    """Extend the session by marking the session as modified."""
    if request.method == "POST":
        request.session.modified = True  # Mark the session as modified to reset its timer
        return JsonResponse({"status": "success", "message": "Session extended."})
    return JsonResponse({"status": "error", "message": "Invalid request method."}, status=405)
