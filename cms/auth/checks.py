from collections.abc import Iterable
from typing import TYPE_CHECKING, Any

from django.conf import settings
from django.core.checks import Error, register

if TYPE_CHECKING:
    from django.apps import AppConfig
    from django.conf import LazySettings


def _check_aws_cognito(errors: list, settings_obj: "LazySettings") -> None:
    aws_cognito_enabled = getattr(settings_obj, "AWS_COGNITO_LOGIN_ENABLED", False)
    if aws_cognito_enabled:
        cognito_settings: list[tuple[str, str, str]] = [
            ("AWS_COGNITO_USER_POOL_ID", "eu-west-2_xxxxxxxxx", "auth.E001"),
            ("AWS_COGNITO_APP_CLIENT_ID", "1234567890abcdefghijklmnop", "auth.E002"),
            ("AWS_REGION", "eu-west-2", "auth.E003"),
            ("AUTH_TOKEN_REFRESH_URL", "http://localhost:29500/tokens/self", "auth.E004"),
            ("LOGOUT_REDIRECT_URL", "http://localhost:29500/logout", "auth.E005"),
        ]
        for setting, hint_value, error_id in cognito_settings:
            value = getattr(settings_obj, setting, None)
            if not value:
                errors.append(
                    Error(
                        f"{setting} is required when AWS_COGNITO_LOGIN_ENABLED is True.",
                        hint=f"Set {setting} to e.g. '{hint_value}'.",
                        id=error_id,
                    )
                )


def _check_session_config(errors: list, settings_obj: "LazySettings") -> None:
    session_cookie_age = getattr(settings_obj, "SESSION_COOKIE_AGE", None)
    session_renewal_offset = getattr(settings_obj, "SESSION_RENEWAL_OFFSET_SECONDS", None)
    if session_cookie_age and session_renewal_offset and session_renewal_offset >= session_cookie_age:
        errors.append(
            Error(
                f"SESSION_RENEWAL_OFFSET_SECONDS ({session_renewal_offset}) should be less than "
                f"SESSION_COOKIE_AGE ({session_cookie_age}).",
                hint="Set SESSION_RENEWAL_OFFSET_SECONDS to a value smaller than SESSION_COOKIE_AGE.",
                id="auth.E006",
            )
        )


def _check_identity_api(errors: list, settings_obj: "LazySettings") -> None:
    identity_api_url = getattr(settings_obj, "IDENTITY_API_BASE_URL", None)
    team_sync_enabled = getattr(settings_obj, "AWS_COGNITO_TEAM_SYNC_ENABLED", False)
    if identity_api_url and team_sync_enabled:
        service_auth_token = getattr(settings_obj, "SERVICE_AUTH_TOKEN", None)
        if not service_auth_token:
            errors.append(
                Error(
                    (
                        "SERVICE_AUTH_TOKEN is not set but IDENTITY_API_BASE_URL is configured and "
                        "AWS_COGNITO_TEAM_SYNC_ENABLED is True."
                    ),
                    hint="Set SERVICE_AUTH_TOKEN for API authentication.",
                    id="auth.E007",
                )
            )


def _check_team_sync(errors: list, settings_obj: "LazySettings") -> None:
    team_sync_enabled = getattr(settings_obj, "AWS_COGNITO_TEAM_SYNC_ENABLED", False)
    if team_sync_enabled:
        team_sync_frequency = getattr(settings_obj, "AWS_COGNITO_TEAM_SYNC_FREQUENCY", None)
        if team_sync_frequency is not None and team_sync_frequency < 1:
            errors.append(
                Error(
                    f"AWS_COGNITO_TEAM_SYNC_FREQUENCY must be at least 1 (got {team_sync_frequency}).",
                    hint="Set AWS_COGNITO_TEAM_SYNC_FREQUENCY to a positive integer.",
                    id="auth.E008",
                )
            )


@register()
def check_auth_settings(app_configs: Iterable["AppConfig"] | None, **kwargs: Any) -> list[Error]:  # pylint: disable=unused-argument
    """Check that required auth settings are properly configured."""
    errors: list[Error] = []
    _check_aws_cognito(errors, settings)
    _check_session_config(errors, settings)
    return errors


@register()
def check_identity_api_settings(app_configs: Iterable["AppConfig"] | None, **kwargs: Any) -> list[Error]:  # pylint: disable=unused-argument
    """Check identity API, team sync, and group name settings."""
    errors: list[Error] = []
    _check_identity_api(errors, settings)
    _check_team_sync(errors, settings)
    return errors
