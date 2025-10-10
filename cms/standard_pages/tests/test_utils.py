from unittest.mock import patch

from django.test import TestCase
from wagtail.coreutils import get_dummy_request

from cms.standard_pages.utils import get_cookies_page_url


class UtilsTestCase(TestCase):
    def setUp(self):
        self.request = get_dummy_request()

    def test_get_cookies_page_url_english(self):
        self.request.LANGUAGE_CODE = "en-gb"
        cookies_page_url = get_cookies_page_url(self.request)
        self.assertEqual(cookies_page_url, "/cookies")

    def test_get_cookies_page_url_welsh(self):
        self.request.LANGUAGE_CODE = "cy"
        cookies_page_url = get_cookies_page_url(self.request)
        self.assertEqual(cookies_page_url, "/cy/cookies")

    def test_get_cookies_page_url_unsupported_language(self):
        # French is not currently supported, so should fall back to English
        self.request.LANGUAGE_CODE = "fr"
        cookies_page_url = get_cookies_page_url(self.request)
        self.assertEqual(cookies_page_url, "/cookies")

    def test_get_cookies_page_url_missing_language_code(self):
        # If the request is missing a language code it should fall back to English
        # get_dummy_request already returns a WSGIRequest without a LANGUAGE_CODE attribute
        self.assertIsNone(getattr(self.request, "LANGUAGE_CODE", None))
        cookies_page_url = get_cookies_page_url(self.request)
        self.assertEqual(cookies_page_url, "/cookies")

    def test_get_cookies_page_url_unexpected_error(self):
        # Simulate an unexpected error and verify the default URL is returned

        # Test with welsh to verify it is falling back on default
        self.request.LANGUAGE_CODE = "cy"
        with patch("cms.standard_pages.utils._cached_get_cookies_page_url", side_effect=Exception):
            cookies_page_url = get_cookies_page_url(self.request)
        self.assertEqual(cookies_page_url, "/cookies")

        # Verify that the fallback default URL was not cached for the Welsh language code,
        # when no error occurs, we should get the correct Welsh URL
        second_cookies_page_url = get_cookies_page_url(self.request)
        self.assertEqual(second_cookies_page_url, "/cy/cookies")
