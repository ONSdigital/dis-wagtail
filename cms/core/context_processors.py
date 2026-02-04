from typing import TYPE_CHECKING, Any

from django.conf import settings

from cms.auth.utils import get_auth_config
from cms.standard_pages.utils import get_cookies_page_url

if TYPE_CHECKING:
    from django.http import HttpRequest


def global_vars(request: HttpRequest) -> dict[str, Any]:
    """Set our global variables to use in templates."""
    return {
        "GOOGLE_TAG_MANAGER_CONTAINER_ID": settings.GOOGLE_TAG_MANAGER_CONTAINER_ID,
        # Cookie banner settings
        "ONS_COOKIE_BANNER_SERVICE_NAME": settings.ONS_COOKIE_BANNER_SERVICE_NAME,
        "SEO_NOINDEX": settings.SEO_NOINDEX,
        "LANGUAGE_CODE": settings.LANGUAGE_CODE,
        "IS_EXTERNAL_ENV": settings.IS_EXTERNAL_ENV,
        "AWS_COGNITO_LOGIN_ENABLED": settings.AWS_COGNITO_LOGIN_ENABLED,
        "WAGTAIL_CORE_ADMIN_LOGIN_ENABLED": settings.WAGTAIL_CORE_ADMIN_LOGIN_ENABLED,
        "AUTH_CONFIG": get_auth_config(),
        "DEFAULT_OG_IMAGE_URL": settings.DEFAULT_OG_IMAGE_URL,
        "CONTACT_US_URL": settings.CONTACT_US_URL,
        "BACKUP_SITE_URL": settings.BACKUP_SITE_URL,
        "SEARCH_PAGE_URL": settings.SEARCH_PAGE_URL,
        "COOKIES_PAGE_URL": get_cookies_page_url(getattr(request, "LANGUAGE_CODE", settings.LANGUAGE_CODE)),
    }
