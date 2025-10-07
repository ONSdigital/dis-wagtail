from django.test import TestCase

from cms.standard_pages.utils import get_cookies_page_url


class UtilsTestCase(TestCase):
    def test_get_cookies_page_url_english(self):
        cookies_page_url = get_cookies_page_url("en-gb")
        self.assertEqual(cookies_page_url, "/cookies")

    def test_get_cookies_page_url_welsh(self):
        cookies_page_url = get_cookies_page_url("cy")
        self.assertEqual(cookies_page_url, "/cy/cookies")

    def test_get_cookies_page_url_fallback(self):
        # French is not currently supported, so should fall back to English
        cookies_page_url = get_cookies_page_url("fr")
        self.assertEqual(cookies_page_url, "/cookies")
