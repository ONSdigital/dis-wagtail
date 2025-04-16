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

JWT_SESSION_ID_KEY = "jwt_session_id"


class ONSAuthMiddleware(AuthenticationMiddleware):
    """Middleware for handling authentication via JWT tokens from AWS Cognito
    or the default Django authentication.

    When AWS_COGNITO_LOGIN_ENABLED is active, this middleware extracts tokens from cookies, validates
    them, checks for any mismatch (client IDs, usernames, or token identifiers), and logs out the user
    if an issue is encountered.
    """

    def process_request(self, request: "HttpRequest") -> None:
        """Process each incoming HTTP request to validate JWT tokens and ensure
        user authentication.
        """
        super().process_request(request)

        if not settings.AWS_COGNITO_LOGIN_ENABLED:
            self._handle_cognito_disabled(request)
            return

        # Extract tokens from cookies.
        access_token = request.COOKIES.get(settings.ACCESS_TOKEN_COOKIE_NAME)
        id_token = request.COOKIES.get(settings.ID_TOKEN_COOKIE_NAME)
        if not access_token or not id_token:
            self._handle_unauthenticated_user(request)
            return

        # Validate the tokens.
        access_payload = validate_jwt(access_token, token_type="access")  # noqa: S106
        id_payload = validate_jwt(id_token, token_type="id")  # noqa: S106
        if not access_payload or not id_payload:
            logger.info("Invalid or expired JWT tokens; logging out user.")
            logout(request)
            return

        # Token and session integrity checks.
        is_valid = self._validate_token_session_consistency(
            request=request, access_payload=access_payload, id_payload=id_payload
        )
        if not is_valid:
            logout(request)
            return

        # Check if the session is up-to-date.
        access_jti = access_payload["jti"]
        id_jti = id_payload["jti"]
        if request.user.is_authenticated and request.session.get(JWT_SESSION_ID_KEY) == f"{access_jti}{id_jti}":
            # The session is up-to-date.
            return

        # Update the session with token identifiers.
        request.session[JWT_SESSION_ID_KEY] = f"{access_jti}{id_jti}"

        # Authenticate and log in the user.
        self._authenticate_user(request, id_payload)

    def _validate_token_session_consistency(
        self, *, request: "HttpRequest", access_payload: Mapping, id_payload: Mapping
    ) -> bool:
        # Ensure the client IDs match.
        if not self._validate_client_ids(client_id=access_payload["client_id"], audience=id_payload["aud"]):
            return False

        # Confirm tokens are issued for the same user.
        access_username = access_payload["username"]
        id_username = id_payload["cognito:username"]
        if access_username != id_username:
            logger.error(
                "Token mismatch: access token username does not match ID token username. Logging out user.",
                extra={"access_username": access_username, "id_username": id_username},
            )
            return False

        # If a user is already authenticated, validate that the session user matches the token user.
        if request.user.is_authenticated and str(request.user.user_id) != id_username:
            logger.error(
                "Authenticated user does not match token user. Logging out user.",
                extra={"user_id": request.user.user_id, "token_user_id": id_username},
            )
            return False

        return True

    @staticmethod
    def _validate_client_ids(*, client_id: str, audience: str) -> bool:
        """Checks that the client_id from the access token and the audience field from the ID token
        match the cognito app client ID.
        """
        expected_client_id = settings.AWS_COGNITO_APP_CLIENT_ID

        if client_id != expected_client_id or audience != expected_client_id:
            logger.error(
                "Token client ID and audience mismatch with app client ID",
                extra={
                    "client_id": client_id,
                    "aud": audience,
                    "expected_client_id": expected_client_id,
                },
            )
            return False
        return True

    @staticmethod
    def _handle_cognito_disabled(request: "HttpRequest") -> None:
        """Processes requests when AWS Cognito authentication is disabled.
        Logs out users that do not have a usable password.
        """
        if request.user.is_authenticated and not request.user.has_usable_password():
            logger.info(
                "AWS Cognito is disabled; logging out user without a usable password",
                extra={"user_id": request.user.user_id},
            )
            logout(request)

    @staticmethod
    def _handle_unauthenticated_user(request: "HttpRequest") -> None:
        """Logs out the user if JWT tokens are missing and the session configuration is unsuitable."""
        if not request.user.is_authenticated:
            return

        if not settings.WAGTAIL_CORE_ADMIN_LOGIN_ENABLED or not request.user.has_usable_password():
            logger.info(
                "Terminating session due to missing JWT tokens or insufficient login configuration (user_id: %s).",
                request.user.user_id,
            )
            logout(request)

    @staticmethod
    def _authenticate_user(request: "HttpRequest", id_payload: Mapping) -> None:
        """Authenticates the user based on the JWT payload.

        Retrieves or creates the user, updates details, assigns appropriate groups, and logs the user in.
        """
        user_id = id_payload["cognito:username"]
        email = id_payload["email"]
        first_name = id_payload.get("given_name", "")
        last_name = id_payload.get("family_name", "")

        user, created = User.objects.get_or_create(
            user_id=user_id,
            defaults={"email": email, "username": email},
        )

        # Update user details.
        user.update_details(email=email, first_name=first_name, last_name=last_name, created=created)

        # Assign groups if provided.
        groups_ids = id_payload.get("cognito:groups") or []
        user.assign_groups_and_teams(groups_ids)

        login(request, user)
