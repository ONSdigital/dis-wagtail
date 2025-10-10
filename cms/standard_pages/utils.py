import logging

from django.conf import settings

logger = logging.getLogger(__name__)
SUPPORTED_LANGUAGE_CODES = {lang[0] for lang in settings.LANGUAGES}
DEFAULT_COOKIES_PAGE_URL = f"/{settings.ONS_COOKIES_PAGE_SLUG}"


def get_cookies_page_url(language_code: str) -> str:
    """Get the relative URL for the cookies page for the given language_code,
    considering subdomain locale routing settings.
    """
    if (
        (not settings.CMS_USE_SUBDOMAIN_LOCALES)
        and language_code != settings.LANGUAGE_CODE
        and language_code in SUPPORTED_LANGUAGE_CODES
    ):
        # Only prefix the URL with the language code if not using subdomain locales and the language code is not the
        # default English and is a supported language
        return f"/{language_code}{DEFAULT_COOKIES_PAGE_URL}"
    return DEFAULT_COOKIES_PAGE_URL
