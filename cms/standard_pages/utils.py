import logging
from functools import lru_cache

from django.conf import settings
from django.http import HttpRequest

from cms.standard_pages.models import CookiesPage

logger = logging.getLogger(__name__)
SUPPORTED_LANGUAGE_CODES = {lang[0] for lang in settings.LANGUAGES}
DEFAULT_COOKIES_PAGE_URL = f"/{settings.ONS_COOKIES_PAGE_DEFAULT_SLUG}"


def get_cookies_page_url(request: HttpRequest) -> str:
    """Get the URL of the cookies page for the given request's language code.
    The URL is cached for performance, as this needs to be called on every page load.
    This is a wrapper around the cached function to handle any unexpected errors gracefully, since this is called for
    every page load, we need to ensure that any errors do not prevent the page from loading.
    """
    try:
        return _cached_get_cookies_page_url(request)
    except Exception:  # pylint: disable=broad-except
        # The broad except is intentional here, as we want to catch any unexpected errors and log them without
        # preventing a page from loading.
        logger.exception("Error getting cookies page URL")
        return DEFAULT_COOKIES_PAGE_URL


@lru_cache
def _cached_get_cookies_page_url(request: "HttpRequest") -> str:
    """Get the URL of the cookies page for the given language code.
    Note that this is cached for performance, as this needs to be called on every page load.
    This creates some edge cases we add or change cookies pages (especially if we change their slug) where instances may
    use an old URL until the cache is cleared (by a server restart). This is considered an acceptable trade-off, as
    the cookies pages are static and their routes are unlikely to change often.
    """
    language_code = getattr(request, "LANGUAGE_CODE", settings.LANGUAGE_CODE)
    if language_code not in SUPPORTED_LANGUAGE_CODES:
        # Fallback to the default english language code if the provided language code is not supported
        language_code = settings.LANGUAGE_CODE
    try:
        cookies_page = CookiesPage.objects.get(locale__language_code=language_code)
    except CookiesPage.DoesNotExist:
        logger.error("Cookies page does not exist for language code", extra={language_code: language_code})
        return settings.ONS_COOKIES_PAGE_DEFAULT_SLUG
    cookies_page_url = cookies_page.get_url(request=request)
    return cookies_page_url if cookies_page_url else DEFAULT_COOKIES_PAGE_URL
