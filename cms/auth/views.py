from typing import TYPE_CHECKING, Any

from django.conf import settings
from django.contrib import messages
from django.http import HttpResponse
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect
from wagtail.admin.views.account import LogoutView

if TYPE_CHECKING:
    from django.http import HttpRequest


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
        # These will be replaced by call to the logout endpoint in the auth service
        # which will revoke the access token and delete cookies
        response.delete_cookie(settings.ACCESS_TOKEN_COOKIE_NAME)
        response.delete_cookie(settings.ID_TOKEN_COOKIE_NAME)
        response.delete_cookie(settings.REFRESH_TOKEN_COOKIE_NAME)

        return response
