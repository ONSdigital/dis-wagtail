import logging
from collections.abc import Iterable, Mapping
from typing import TYPE_CHECKING

import jwt
from django.conf import settings
from django.contrib.auth import get_user_model, login, logout
from django.contrib.auth.middleware import AuthenticationMiddleware
from django.contrib.auth.models import Group
from jwt import ExpiredSignatureError, InvalidTokenError

from cms.teams.models import Team

if TYPE_CHECKING:
    from django.http import HttpRequest

    from cms.users.models import User as UserModel

logger = logging.getLogger(__name__)


User = get_user_model()


def extract_and_validate_token(token: str, token_type: str) -> dict | None:
    """Extract and validate a JWT token using the appropriate public key."""
    try:
        token = token.split(" ")[1] if token.startswith("Bearer ") else token
        kid = jwt.get_unverified_header(token).get("kid")
        if not kid:
            raise ValueError(f"{token_type} is missing 'kid' in the header.")

        # public_key = get_public_key(kid)
        # Retrieve and validate token payload
        payload: dict = jwt.decode(
            token,
            # public_key,  # Uncomment for production
            algorithms=["RS256"],
            options={
                "verify_iss": False,  # Set to True in production
                "verify_exp": True,
                "verify_signature": False,  # Set to True in production
            },
        )
        return payload
    except ExpiredSignatureError:
        logger.exception("%s has expired", token_type)
    except InvalidTokenError:
        logger.exception("Invalid %s", token_type)
    except Exception:  # pylint: disable=broad-except
        logger.exception("Failed to validate %s", token_type)
    return None


def update_user_details(user: "UserModel", email: str, first_name: str, last_name: str, created: bool) -> None:
    """Update user details regardless of whether the user was newly created."""
    user.email = email
    user.first_name = first_name
    user.last_name = last_name
    if created:
        user.set_unusable_password()


def assign_groups(user: "UserModel", cognito_groups: Iterable[str]) -> None:
    """Assign groups to the user based on their Cognito groups."""
    publishing_officer_group = Group.objects.get(name=settings.PUBLISHING_OFFICERS_GROUP_NAME)
    viewer_group = Group.objects.get(name=settings.VIEWERS_GROUP_NAME)

    user.is_superuser = "role-admin" in cognito_groups
    user.is_staff = user.is_superuser

    if "role-publisher" in cognito_groups:
        user.groups.add(publishing_officer_group)
    else:
        user.groups.remove(publishing_officer_group)

    user.groups.add(viewer_group)  # Always add viewer group


def assign_teams(user: "UserModel", cognito_groups: Iterable[str]) -> None:
    """Assign teams to the user based on their Cognito groups."""
    teams_to_add = set(cognito_groups) - set(settings.ROLE_GROUP_IDS)
    existing_teams = {team.identifier: team for team in Team.objects.filter(identifier__in=teams_to_add)}
    missing_team_ids = teams_to_add - set(existing_teams.keys())

    # Create missing teams in bulk
    if missing_team_ids:
        missing_teams = [
            Team(
                identifier=team_id,
                name=team_id.replace("-", " ").title(),  # Temporary name, will be updated on sync
            )
            for team_id in missing_team_ids
        ]
        Team.objects.bulk_create(missing_teams)
        # Refresh the queryset to include newly created teams
        new_teams = Team.objects.filter(identifier__in=missing_team_ids)
        existing_teams |= {team.identifier: team for team in new_teams}

    teams_for_user = list(existing_teams.values())
    user.teams.set(teams_for_user)


class ONSAuthMiddleware(AuthenticationMiddleware):
    """Middleware for JWT or Default Django authentication."""

    def process_request(self, request: "HttpRequest") -> None:
        super().process_request(request)

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

        if request.user.is_authenticated:
            return  # User already authenticated

        self._authenticate_user(request, access_payload, id_payload)

    @staticmethod
    def _handle_unauthenticated_user(request: "HttpRequest") -> None:
        """Handle unauthenticated users, including logout if necessary."""
        if not request.user.is_authenticated:
            return

        if not settings.WAGTAIL_CORE_ADMIN_LOGIN_ENABLED or not request.user.has_usable_password():
            logout(request)

    @staticmethod
    def _authenticate_user(request: "HttpRequest", access_payload: Mapping, id_payload: Mapping) -> None:
        """Authenticate user based on token payloads."""
        username = access_payload.get("username") or id_payload.get("cognito:username")
        email = id_payload.get("email")
        first_name = id_payload.get("given_name", "")
        last_name = id_payload.get("family_name", "")

        if not username or not email:
            return

        # Get or create user and update details
        user, created = User.objects.get_or_create(username=email, defaults={"email": email})
        update_user_details(user, email, first_name, last_name, created)

        # Assign groups
        cognito_groups = access_payload.get("cognito:groups", [])
        assign_groups(user, cognito_groups)

        # Assign teams
        assign_teams(user, cognito_groups)

        # Save any changes to the user
        user.save()

        # Authenticate user
        login(request, user)
