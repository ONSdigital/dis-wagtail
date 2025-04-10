from django.test import TestCase, override_settings
from wagtail.coreutils import get_dummy_request
from wagtail.models import Locale

from cms.core.templatetags.util_tags import (
    get_hreflangs,
    get_translation_urls,
)
from cms.home.models import HomePage


class LangageTemplateTagTests(TestCase):
    def test_get_translation_urls(self):
        """Test that get_translation_urls returns the correct URLs."""
        # Mock request and page
        request = get_dummy_request()
        page = HomePage.objects.first()

        # Call the function
        urls = get_translation_urls({"request": request, "page": page})

        # Check the output format
        self.assertIsInstance(urls, list)
        for url in urls:
            self.assertIn("url", url)
            self.assertIn("isoCode", url)
            self.assertIn("text", url)
            self.assertIn("current", url)

        self.assertEqual(urls[0]["url"], "/")
        self.assertEqual(urls[0]["isoCode"], "en")
        self.assertEqual(urls[0]["text"], "English")
        self.assertEqual(urls[0]["current"], True)
        self.assertEqual(urls[1]["current"], False)

    def test_get_hreflangs(self):
        """Test that get_hreflangs returns the correct hreflang URLs."""
        # Mock request and page
        request = get_dummy_request()
        page = HomePage.objects.first()

        # Call the function
        hreflangs = get_hreflangs({"request": request, "page": page})

        # Check the output format
        self.assertIsInstance(hreflangs, list)
        self.assertEqual(len(hreflangs), 2)

        for hreflang in hreflangs:
            self.assertIn("url", hreflang)
            self.assertIn("lang", hreflang)

        self.assertEqual(hreflangs[0]["url"], "/")
        self.assertEqual(hreflangs[0]["lang"], "en-gb")
        self.assertEqual(hreflangs[1]["lang"], "cy")
        self.assertEqual(hreflangs[1]["url"], "/cy/")

    @override_settings(LANGUAGE_CODE="pl")
    @override_settings(LANGUAGES=[("pl", "Polish"), ("cy", "Welsh")])
    @override_settings(WAGTAIL_CONTENT_LANGUAGES=[("pl", "Polish"), ("cy", "Welsh")])
    def test_get_hreflangs_with_different_base_locale(self):
        """Test that get_hreflangs returns the correct hreflang URLs with a different base locale."""
        # Replace the default locale with Polish
        main_locale = Locale.objects.filter(language_code="en-gb").first()
        main_locale.language_code = "pl"
        main_locale.save()

        # Mock request and page
        request = get_dummy_request()
        page = HomePage.objects.first()

        # Call the function
        hreflangs = get_hreflangs({"request": request, "page": page})

        # Check the output format
        self.assertIsInstance(hreflangs, list)
        self.assertEqual(len(hreflangs), 2)

        for hreflang in hreflangs:
            self.assertIn("url", hreflang)
            self.assertIn("lang", hreflang)

        self.assertEqual(hreflangs[0]["url"], "/")
        self.assertEqual(hreflangs[0]["lang"], "pl")
        self.assertEqual(hreflangs[1]["lang"], "cy")
        self.assertEqual(hreflangs[1]["url"], "/cy/")
