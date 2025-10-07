from django.conf import settings
from wagtail.models import Locale

from cms.standard_pages.models import CookiesPage


def get_cookies_page_url(language_code: str) -> str:
    if language_code not in (supported_lang[0] for supported_lang in settings.LANGUAGES):
        # Fallback to the default english language code if the provided language code is not supported
        language_code = settings.LANGUAGE_CODE
    # Cookies pages must exist for supported languages
    cookies_page = CookiesPage.objects.get(locale=Locale.objects.get(language_code=language_code))
    return cookies_page.get_url()
