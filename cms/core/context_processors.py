from typing import TYPE_CHECKING, Any

from django.conf import settings

from cms.auth.utils import get_auth_config

if TYPE_CHECKING:
    from django.http import HttpRequest


def global_vars(request: "HttpRequest") -> dict[str, Any]:
    """Set our global variables to use in templates."""
    return {
        "GOOGLE_TAG_MANAGER_CONTAINER_ID": settings.GOOGLE_TAG_MANAGER_CONTAINER_ID,
        # Cookie banner settings
        "ONS_COOKIE_BANNER_SERVICE_NAME": settings.ONS_COOKIE_BANNER_SERVICE_NAME,
        "MANAGE_COOKIE_SETTINGS_URL": settings.MANAGE_COOKIE_SETTINGS_URL,
        "SEO_NOINDEX": settings.SEO_NOINDEX,
        "LANGUAGE_CODE": settings.LANGUAGE_CODE,
        "IS_EXTERNAL_ENV": settings.IS_EXTERNAL_ENV,
        "AWS_COGNITO_LOGIN_ENABLED": settings.AWS_COGNITO_LOGIN_ENABLED,
        "WAGTAIL_CORE_ADMIN_LOGIN_ENABLED": settings.WAGTAIL_CORE_ADMIN_LOGIN_ENABLED,
        "AUTH_CONFIG": get_auth_config(),
        "FALLBACK_OG_IMAGE_URL": settings.FALLBACK_OG_IMAGE_URL,
    }
