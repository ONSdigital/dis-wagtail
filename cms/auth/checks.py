from collections.abc import Iterable
from typing import Any

from django.apps import AppConfig
from django.conf import settings
from django.core.checks import Error, register


def _check_middleware(errors: list, settings_obj) -> None:
    if not settings_obj.IS_EXTERNAL_ENV:
        middleware = getattr(settings_obj, "MIDDLEWARE", [])
        auth_middleware = "cms.auth.middleware.ONSAuthMiddleware"
        if auth_middleware not in middleware:
            errors.append(
                Error(
                    f"{auth_middleware} is not in MIDDLEWARE for internal environment.",
                    hint=f"Add '{auth_middleware}' to MIDDLEWARE.",
                    id="auth.E006",
                )
            )


def _check_aws_cognito(errors: list, settings_obj) -> None:
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


def _check_auth_backends(errors: list, settings_obj) -> None:
    auth_backends = getattr(settings_obj, "AUTHENTICATION_BACKENDS", [])
    if settings_obj.IS_EXTERNAL_ENV and auth_backends:
        errors.append(
            Warning(
                "AUTHENTICATION_BACKENDS should be empty for external environments.",
                hint="Clear AUTHENTICATION_BACKENDS when IS_EXTERNAL_ENV is True.",
                id="auth.W001",  # TODO: Check if this should be an Error instead of a Warning
            )
        )


def _check_cookie_names(errors: list, settings_obj) -> None:
    # TODO: Check if this should be an Error instead of a Warning
    cookie_names = [
        ("ACCESS_TOKEN_COOKIE_NAME", "auth.W002"),
        ("REFRESH_TOKEN_COOKIE_NAME", "auth.W003"),
        ("ID_TOKEN_COOKIE_NAME", "auth.W004"),
    ]
    for cookie_setting, warning_id in cookie_names:
        if not getattr(settings_obj, cookie_setting, None):
            errors.append(
                Warning(
                    f"{cookie_setting} is not defined.",
                    hint=f"Set {cookie_setting} to define the cookie name.",
                    id=warning_id,
                )
            )


def _check_csrf_trusted_origins(errors: list, settings_obj) -> None:
    aws_cognito_enabled = getattr(settings_obj, "AWS_COGNITO_LOGIN_ENABLED", False)
    if aws_cognito_enabled:
        csrf_trusted_origins = getattr(settings_obj, "CSRF_TRUSTED_ORIGINS", [])
        wagtail_login_url = getattr(settings_obj, "WAGTAILADMIN_LOGIN_URL", "")
        if wagtail_login_url.startswith(("http://", "https://")):
            from urllib.parse import urlparse

            parsed = urlparse(wagtail_login_url)
            origin = f"{parsed.scheme}://{parsed.netloc}"
            if origin not in csrf_trusted_origins:
                errors.append(
                    Warning(
                        f"WAGTAILADMIN_LOGIN_URL points to '{origin}' but it's not in CSRF_TRUSTED_ORIGINS.",
                        hint=f"Add '{origin}' to CSRF_TRUSTED_ORIGINS.",
                        id="auth.W005",
                    )
                )


def _check_session_config(errors: list, settings_obj) -> None:
    session_cookie_age = getattr(settings_obj, "SESSION_COOKIE_AGE", None)
    session_renewal_offset = getattr(settings_obj, "SESSION_RENEWAL_OFFSET_SECONDS", None)
    if session_cookie_age and session_renewal_offset and session_renewal_offset >= session_cookie_age:
        errors.append(
            Warning(
                f"SESSION_RENEWAL_OFFSET_SECONDS ({session_renewal_offset}) should be less than "
                f"SESSION_COOKIE_AGE ({session_cookie_age}).",
                hint="Set SESSION_RENEWAL_OFFSET_SECONDS to a value smaller than SESSION_COOKIE_AGE.",
                id="auth.W006",  # TODO: Check if this should be an Error instead of a Warning
            )
        )


def _check_identity_api(errors: list, settings_obj) -> None:
    identity_api_url = getattr(settings_obj, "IDENTITY_API_BASE_URL", None)
    if identity_api_url:
        service_auth_token = getattr(settings_obj, "SERVICE_AUTH_TOKEN", None)
        if not service_auth_token:
            errors.append(
                Warning(
                    "SERVICE_AUTH_TOKEN is not set but IDENTITY_API_BASE_URL is configured.",
                    hint="Set SERVICE_AUTH_TOKEN for API authentication.",
                    id="auth.W001",  # TODO: Check if this should be an Error instead of a Warning
                )
            )


def _check_team_sync(errors: list, settings_obj) -> None:
    team_sync_enabled = getattr(settings_obj, "AWS_COGNITO_TEAM_SYNC_ENABLED", False)
    if team_sync_enabled:
        team_sync_frequency = getattr(settings_obj, "AWS_COGNITO_TEAM_SYNC_FREQUENCY", None)
        if team_sync_frequency is not None and team_sync_frequency < 1:
            errors.append(
                Error(
                    f"AWS_COGNITO_TEAM_SYNC_FREQUENCY must be at least 1 (got {team_sync_frequency}).",
                    hint="Set AWS_COGNITO_TEAM_SYNC_FREQUENCY to a positive integer.",
                    id="auth.E001",
                )
            )


def _check_group_names(errors: list, settings_obj) -> None:
    required_groups = [
        ("PUBLISHING_ADMIN_GROUP_NAME", "auth.E002"),
        ("PUBLISHING_OFFICER_GROUP_NAME", "auth.E003"),
        ("VIEWERS_GROUP_NAME", "auth.E004"),
    ]
    for group_setting, error_id in required_groups:
        if not getattr(settings_obj, group_setting, None):
            errors.append(
                Error(
                    f"{group_setting} is not defined.",
                    hint=f"Set {group_setting} to define the user group name.",
                    id=error_id,
                )
            )


@register()
def check_auth_settings(app_configs: Iterable[AppConfig] | None, **kwargs: Any) -> list[Error]:  # pylint: disable=unused-argument
    """Check that required auth settings are properly configured."""
    errors: list[Error] = []
    _check_middleware(errors, settings)
    _check_aws_cognito(errors, settings)
    _check_auth_backends(errors, settings)
    _check_cookie_names(errors, settings)
    _check_csrf_trusted_origins(errors, settings)
    _check_session_config(errors, settings)
    return errors


@register()
def check_identity_api_settings(app_configs: Iterable[AppConfig] | None, **kwargs: Any) -> list[Error]:  # pylint: disable=unused-argument
    """Check identity API, team sync, and group name settings."""
    errors: list[Error] = []
    _check_identity_api(errors, settings)
    _check_team_sync(errors, settings)
    _check_group_names(errors, settings)
    return errors
