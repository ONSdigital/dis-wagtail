from collections.abc import Iterable
from typing import TYPE_CHECKING, Any

from django.conf import settings
from django.core.checks import Error, register

if TYPE_CHECKING:
    from django.apps import AppConfig


@register()
def check_aws_cognito(app_configs: Iterable[AppConfig] | None, **kwargs: Any) -> list[Error]:  # pylint: disable=unused-argument
    errors: list[Error] = []

    if not getattr(settings, "AWS_COGNITO_LOGIN_ENABLED", False):
        return errors

    cognito_settings: list[tuple[str, str, str]] = [
        ("AWS_COGNITO_USER_POOL_ID", "eu-west-2_xxxxxxxxx", "auth.E001"),
        ("AWS_COGNITO_APP_CLIENT_ID", "the-cognito-app-client-id", "auth.E002"),
        ("AWS_REGION", "eu-west-2", "auth.E003"),
        ("AUTH_TOKEN_REFRESH_URL", "http://localhost:29500/tokens/self", "auth.E004"),
        ("LOGOUT_REDIRECT_URL", "http://localhost:29500/logout", "auth.E005"),
    ]
    for setting, hint_value, error_id in cognito_settings:
        value = getattr(settings, setting, None)
        if not value:
            errors.append(
                Error(
                    f"{setting} is required when AWS_COGNITO_LOGIN_ENABLED is True.",
                    hint=f"Set {setting} to an appropriate value. e.g. '{hint_value}'.",
                    id=error_id,
                )
            )

    return errors


@register()
def check_session_config(app_configs: Iterable[AppConfig] | None, **kwargs: Any) -> list[Error]:  # pylint: disable=unused-argument
    errors: list[Error] = []
    session_cookie_age = getattr(settings, "SESSION_COOKIE_AGE", None)
    session_renewal_offset = getattr(settings, "SESSION_RENEWAL_OFFSET_SECONDS", None)

    if session_cookie_age and session_renewal_offset and session_renewal_offset >= session_cookie_age:
        errors.append(
            Error(
                f"SESSION_RENEWAL_OFFSET_SECONDS ({session_renewal_offset}) should be less than "
                f"SESSION_COOKIE_AGE ({session_cookie_age}).",
                hint="Set SESSION_RENEWAL_OFFSET_SECONDS to a value smaller than SESSION_COOKIE_AGE.",
                id="auth.E006",
            )
        )

    return errors


@register()
def check_identity_api(app_configs: Iterable[AppConfig] | None, **kwargs: Any) -> list[Error]:  # pylint: disable=unused-argument
    errors: list[Error] = []
    cognito_enabled = getattr(settings, "AWS_COGNITO_LOGIN_ENABLED", False)
    identity_api_url = getattr(settings, "IDENTITY_API_BASE_URL", None)
    team_sync_enabled = getattr(settings, "AWS_COGNITO_TEAM_SYNC_ENABLED", False)
    service_auth_token = getattr(settings, "SERVICE_AUTH_TOKEN", None)

    # Validate IDENTITY_API_BASE_URL is set if either Cognito or Team Sync is enabled
    if (cognito_enabled or team_sync_enabled) and not identity_api_url:
        errors.append(
            Error(
                (
                    "IDENTITY_API_BASE_URL is required when AWS_COGNITO_LOGIN_ENABLED or "
                    "AWS_COGNITO_TEAM_SYNC_ENABLED is True."
                ),
                hint="Set IDENTITY_API_BASE_URL to the identity API endpoint.",
                id="auth.E007",
            )
        )

    # If team sync is enabled, SERVICE_AUTH_TOKEN must be set
    if team_sync_enabled and not service_auth_token:
        errors.append(
            Error(
                ("SERVICE_AUTH_TOKEN is required when AWS_COGNITO_TEAM_SYNC_ENABLED is True."),
                hint="Set SERVICE_AUTH_TOKEN for API authentication.",
                id="auth.E009",
            )
        )

    return errors


@register()
def check_team_sync(app_configs: Iterable[AppConfig] | None, **kwargs: Any) -> list[Error]:  # pylint: disable=unused-argument
    errors: list[Error] = []

    if not getattr(settings, "AWS_COGNITO_TEAM_SYNC_ENABLED", False):
        return errors

    team_sync_frequency = getattr(settings, "AWS_COGNITO_TEAM_SYNC_FREQUENCY", None)
    if team_sync_frequency is not None and team_sync_frequency < 1:
        errors.append(
            Error(
                f"AWS_COGNITO_TEAM_SYNC_FREQUENCY must be at least 1 minute (got {team_sync_frequency}).",
                hint="Set AWS_COGNITO_TEAM_SYNC_FREQUENCY to a positive integer.",
                id="auth.E008",
            )
        )

    return errors
