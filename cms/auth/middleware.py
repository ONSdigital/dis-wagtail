import logging
from collections.abc import Mapping
from typing import TYPE_CHECKING

from django.conf import settings
from django.contrib.auth import get_user_model, login, logout
from django.contrib.auth.middleware import AuthenticationMiddleware

from cms.auth.utils import (
    extract_and_validate_token,
)

if TYPE_CHECKING:
    from django.http import HttpRequest


logger = logging.getLogger(__name__)


User = get_user_model()


class ONSAuthMiddleware(AuthenticationMiddleware):
    """Middleware for JWT or Default Django authentication."""

    def process_request(self, request: "HttpRequest") -> None:
        super().process_request(request)

        if not settings.AWS_COGNITO_LOGIN_ENABLED:
            return

        # Extract tokens from cookies
        access_token = request.COOKIES.get(settings.ACCESS_TOKEN_COOKIE_NAME)
        id_token = request.COOKIES.get(settings.ID_TOKEN_COOKIE_NAME)

        if not access_token or not id_token:
            self._handle_unauthenticated_user(request)
            return

        # Validate tokens
        access_payload = extract_and_validate_token(access_token, settings.ACCESS_TOKEN_COOKIE_NAME)
        id_payload = extract_and_validate_token(id_token, settings.ID_TOKEN_COOKIE_NAME)

        if not access_payload or not id_payload:
            if request.user.is_authenticated:
                # Log out user if token has become invalid or expired
                logout(request)

            return

        access_payload_username = access_payload.get("username")
        id_payload_username = id_payload.get("cognito:username")
        email = id_payload.get("email")

        # if required fields are missing or the tokens do not match, stop processing
        if (
            not all([access_payload_username, id_payload_username, email])
            or access_payload_username != id_payload_username
        ):
            return

        if request.user.is_authenticated:
            # Check cookie user against token user
            user = User.objects.filter(user_id=id_payload_username).first()
            if user == request.user:
                # User already authenticated and validated
                return

            # If user is not matching currently logged-in user, then
            # log out previous session and authenticate new user
            logout(request)

        self._authenticate_user(request, id_payload)

    @staticmethod
    def _handle_unauthenticated_user(request: "HttpRequest") -> None:
        """Handle unauthenticated users, including logout if necessary."""
        if not request.user.is_authenticated:
            return

        if not settings.WAGTAIL_CORE_ADMIN_LOGIN_ENABLED or not request.user.has_usable_password():
            logout(request)

    @staticmethod
    def _authenticate_user(request: "HttpRequest", id_payload: Mapping) -> None:
        """Authenticate user based on token payloads."""
        user_id = id_payload["cognito:username"]
        email = id_payload["email"]
        first_name = id_payload.get("given_name", "")
        last_name = id_payload.get("family_name", "")

        # Get or create user and update details
        user, created = User.objects.get_or_create(user_id=user_id, defaults={"email": email, "username": email})
        user.update_details(email=email, first_name=first_name, last_name=last_name, created=created)

        # Assign Django user groups and preview teams
        groups_ids = id_payload.get("cognito:groups") or []
        user.assign_groups_and_teams(groups_ids)

        # Authenticate user
        login(request, user)
