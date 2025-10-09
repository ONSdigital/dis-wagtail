import logging
from functools import lru_cache

from django.conf import settings

from cms.standard_pages.models import CookiesPage

logger = logging.getLogger(__name__)
SUPPORTED_LANGUAGE_CODES = {lang[0] for lang in settings.LANGUAGES}


@lru_cache
def get_cookies_page_url(language_code: str) -> str | None:
    """Get the URL of the cookies page for the given language code.
    Note that this is cached for performance, as this needs to be called on every page load.
    This creates some edge cases we add or change cookies pages (especially if we change their slug) where instances may
    use an old URL until the cache is cleared (by a server restart). This is considered an acceptable trade-off, as
    the cookies pages are static and their routes are unlikely to change often.
    """
    if language_code not in SUPPORTED_LANGUAGE_CODES:
        # Fallback to the default english language code if the provided language code is not supported
        language_code = settings.LANGUAGE_CODE
    try:
        cookies_page = CookiesPage.objects.get(locale__language_code=language_code)
    except CookiesPage.DoesNotExist:
        logger.error("Cookies page does not exist for language code", extra={language_code: language_code})
        return settings.ONS_COOKIES_PAGE_DEFAULT_URL
    return cookies_page.get_url()
