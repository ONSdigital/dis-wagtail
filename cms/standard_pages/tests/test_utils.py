from django.test import TestCase, override_settings
from wagtail.coreutils import get_dummy_request

from cms.standard_pages.utils import COOKIES_PAGE_URL, get_cookies_page_url


class UtilsTestCase(TestCase):
    def setUp(self):
        self.request = get_dummy_request()

    @override_settings(CMS_USE_SUBDOMAIN_LOCALES=False)
    def test_get_cookies_page_url_english(self):
        cookies_page_url = get_cookies_page_url("en-gb")
        self.assertEqual(cookies_page_url, COOKIES_PAGE_URL)

    @override_settings(CMS_USE_SUBDOMAIN_LOCALES=False)
    def test_get_cookies_page_url_welsh(self):
        cookies_page_url = get_cookies_page_url("cy")
        self.assertEqual(cookies_page_url, f"/cy{COOKIES_PAGE_URL}")

    @override_settings(CMS_USE_SUBDOMAIN_LOCALES=False)
    def test_get_cookies_page_url_unsupported_language(self):
        # French is not currently supported, so should fall back to English
        cookies_page_url = get_cookies_page_url("fr")
        self.assertEqual(cookies_page_url, COOKIES_PAGE_URL)

    def test_get_cookies_page_url_subdomain_locales_english(self):
        # With subdomain locales enabled, all languages should return the default cookies URL
        for language_code in ("en-gb", "cy", "fr", "invalid"):
            with self.subTest(language_code=language_code):
                cookies_page_url = get_cookies_page_url(language_code)
                self.assertEqual(cookies_page_url, COOKIES_PAGE_URL)
