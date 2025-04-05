import logging
from collections.abc import Mapping
from typing import TYPE_CHECKING

from django.conf import settings
from django.contrib.auth import get_user_model, login, logout
from django.contrib.auth.middleware import AuthenticationMiddleware

from cms.auth.utils import validate_jwt

if TYPE_CHECKING:
    from django.http import HttpRequest

logger = logging.getLogger(__name__)
User = get_user_model()


class ONSAuthMiddleware(AuthenticationMiddleware):
    """Middleware for JWT from AWS Cognito or default Django authentication ."""

    def process_request(self, request: "HttpRequest") -> None:
        """Process each request to validate JWT tokens from cookies if AWS Cognito login is enabled."""
        super().process_request(request)

        if not settings.AWS_COGNITO_LOGIN_ENABLED:
            return

        # Extract tokens from cookies
        access_token = request.COOKIES.get(settings.ACCESS_TOKEN_COOKIE_NAME)
        id_token = request.COOKIES.get(settings.ID_TOKEN_COOKIE_NAME)

        if not access_token or not id_token:
            self._handle_unauthenticated_user(request)
            return

        # Validate tokens for access and id.
        access_payload = validate_jwt(access_token, token_type="access")  # noqa: S106
        id_payload = validate_jwt(id_token, token_type="id")  # noqa: S106

        if not access_payload or not id_payload:
            if request.user.is_authenticated:
                logger.info("Invalid or expired tokens detected; logging out user.")
                logout(request)
            return

        # Ensure that tokens belong to the same user.
        access_username = access_payload["username"]
        id_username = id_payload["cognito:username"]
        if access_username != id_username:
            logger.error(
                "Token mismatch: access token username (%s) does not match ID token username (%s).",
                access_username,
                id_username,
            )
            return

        # If a user is already authenticated, verify if the token matches the logged-in user.
        if request.user.is_authenticated:
            user = User.objects.filter(user_id=id_username).first()
            if user == request.user:
                return  # User already authenticated and validated

            logout(request)  # Log out the mismatched session.

        # Authenticate and log in the user using token payload data.
        self._authenticate_user(request, id_payload)

    @staticmethod
    def _handle_unauthenticated_user(request: "HttpRequest") -> None:
        """Logs out the user if necessary based on authentication and admin login configuration."""
        if not request.user.is_authenticated:
            return

        if not settings.WAGTAIL_CORE_ADMIN_LOGIN_ENABLED or not request.user.has_usable_password():
            logger.info(
                "User session terminated due to missing authentication tokens or unsuitable login configuration."
            )
            logout(request)

    @staticmethod
    def _authenticate_user(request: "HttpRequest", id_payload: Mapping) -> None:
        """Authenticates the user based on the JWT payload and updates user details and group assignments."""
        user_id = id_payload["cognito:username"]
        email = id_payload["email"]
        first_name = id_payload.get("given_name", "")
        last_name = id_payload.get("family_name", "")

        # Get or create the user and update details.
        user, created = User.objects.get_or_create(user_id=user_id, defaults={"email": email, "username": email})
        user.update_details(email=email, first_name=first_name, last_name=last_name, created=created)

        # Assign Django user groups and preview teams
        groups_ids = id_payload.get("cognito:groups") or []
        user.assign_groups_and_teams(groups_ids)

        logger.info("Authenticating user %s (new: %s)", user_id, created)
        login(request, user)
