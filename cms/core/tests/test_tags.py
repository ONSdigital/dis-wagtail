from django.conf import settings
from django.test import TestCase, override_settings
from wagtail.coreutils import get_dummy_request
from wagtail.models import Locale, Site

from cms.core.templatetags.page_config_tags import (
    get_hreflangs,
    get_page_config,
    get_translation_urls,
)
from cms.core.templatetags.util_tags import (
    extend,
)
from cms.core.tests.utils import reset_url_caches
from cms.home.models import HomePage


@override_settings(CMS_USE_SUBDOMAIN_LOCALES=False)
class LanguageTemplateTagTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.page = HomePage.objects.first()

    def setUp(self):
        self.dummy_request = get_dummy_request()
        reset_url_caches()

    def tearDown(self):
        reset_url_caches()

    def test_get_translation_urls(self):
        """Test that get_translation_urls returns the correct URLs."""
        # Call the function
        urls = get_translation_urls(self.dummy_request, self.page)

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
        # Call the function
        hreflangs = get_hreflangs(self.dummy_request, self.page)

        # Check the output format
        self.assertIsInstance(hreflangs, list)
        self.assertEqual(len(hreflangs), 2)

        for hreflang in hreflangs:
            self.assertIn("url", hreflang)
            self.assertIn("lang", hreflang)

        self.assertEqual(hreflangs[0]["url"], "/")
        self.assertEqual(hreflangs[0]["lang"], "en-gb")
        self.assertEqual(hreflangs[1]["lang"], "cy")
        self.assertEqual(hreflangs[1]["url"], "/cy")

    @override_settings(
        LANGUAGE_CODE="pl",
        LANGUAGES=[("pl", "Polish"), ("cy", "Welsh")],
        WAGTAIL_CONTENT_LANGUAGES=[("pl", "Polish"), ("cy", "Welsh")],
    )
    def test_get_hreflangs_with_different_base_locale(self):
        """Test that get_hreflangs returns the correct hreflang URLs with a different base locale."""
        # Replace the default locale with Polish
        main_locale = Locale.objects.get(language_code="en-gb")
        main_locale.language_code = "pl"
        main_locale.save()

        # Call the function
        hreflangs = get_hreflangs(self.dummy_request, self.page)

        # Check the output format
        self.assertIsInstance(hreflangs, list)
        self.assertEqual(len(hreflangs), 2)

        for hreflang in hreflangs:
            self.assertIn("url", hreflang)
            self.assertIn("lang", hreflang)

        self.assertEqual(hreflangs[0]["url"], "/")
        self.assertEqual(hreflangs[0]["lang"], "pl")
        self.assertEqual(hreflangs[1]["lang"], "cy")
        self.assertEqual(hreflangs[1]["url"], "/cy")


class ExtendFunctionTest(TestCase):
    """Tests of the `extend()` function.

    This isn't registered as a template tag, but made globally available to be used in
    Python code within Jinja2.
    """

    def test_append(self):
        """Test the original list is modified in place."""
        series = [{"name": "Series 1"}, {"name": "Series 2"}]
        series_item = {"name": "Series 3"}
        extend(series, series_item)
        self.assertEqual([{"name": "Series 1"}, {"name": "Series 2"}, {"name": "Series 3"}], series)

    def test_returns_none(self):
        """Test the return value of the filter.

        This is to ensure the same signature between this and the Nunjucks equivalent.
        """
        series = [{"name": "Series 1"}, {"name": "Series 2"}]
        series_item = {"name": "Series 3"}
        result = extend(series, series_item)
        self.assertIsNone(result)

    def test_bad_first_argument_type(self):
        """Test that an exception is raised if the first argument is not a list.

        This is likely to be called from a template macro, so we can't rely on
        annotations and tooling for type safety.
        """
        with self.assertRaises(TypeError):
            extend("not a list", {"name": "Series 3"})  # type: ignore


@override_settings(CMS_USE_SUBDOMAIN_LOCALES=True)
class PageConfigTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.page = HomePage.objects.get(locale__language_code=settings.LANGUAGE_CODE)
        cls.welsh_home_page = HomePage.objects.get(locale__language_code="cy")

    def setUp(self):
        self.request = get_dummy_request()
        self.request.LANGUAGE_CODE = settings.LANGUAGE_CODE

        self.welsh_request = get_dummy_request(site=Site.objects.get(hostname="cy.ons.localhost"))
        self.welsh_request.LANGUAGE_CODE = "cy"

    def test_page_config(self):
        config = get_page_config({"page": self.page, "request": self.request})

        self.assertEqual(config["bodyClasses"], "template-home-page")
        self.assertEqual(config["title"], f"Office for National Statistics - {self.page.title}")
        self.assertEqual(config["meta"]["canonicalUrl"], "https://ons.localhost/")

        self.assertEqual(
            config["header"]["search"],
            {"id": "search", "form": {"action": "/search", "inputName": "q"}},
        )

    def test_welsh_page_config(self):
        config = get_page_config({"page": self.welsh_home_page, "request": self.welsh_request})

        self.assertEqual(config["bodyClasses"], "template-home-page")
        self.assertEqual(config["title"], f"Swyddfa Ystadegau Gwladol - {self.welsh_home_page.title}")
        self.assertEqual(config["meta"]["canonicalUrl"], "https://ons.localhost/")

        self.assertEqual(
            config["header"]["search"],
            {"id": "search", "form": {"action": "/search", "inputName": "q"}},
        )

    def test_page_title_from_context_overrides_model(self):
        config = get_page_config({"page": self.page, "request": self.request, "page_title": "custom title"})
        self.assertEqual(config["title"], "custom title")

    def test_config_no_page(self):
        with self.assertNumQueries(4):
            config = get_page_config({"request": self.request, "page_title": "not found"})

        self.assertEqual(config["bodyClasses"], "")
        self.assertEqual(config["title"], "not found")
        self.assertEqual(config["header"]["language"], {"languages": []})
        self.assertEqual(config["meta"], {"hrefLangs": [], "canonicalUrl": None})

    @override_settings(
        CACHES={
            "default": {
                "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
                "LOCATION": "test_served_from_cache",
            }
        }
    )
    def test_served_from_cache(self):
        with self.assertNumQueries(8):
            get_page_config({"page": self.page, "request": self.request})

        with self.assertNumQueries(0):
            get_page_config({"page": self.page, "request": self.request})

    @override_settings(
        CACHES={
            "default": {
                "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
                "LOCATION": "test_no_page_served_from_cache",
            }
        }
    )
    def test_no_page_served_from_cache(self):
        with self.assertNumQueries(4):
            get_page_config({"page_title": "not found", "request": self.request})

        with self.assertNumQueries(0):
            get_page_config({"page_title": "not found", "request": self.request})
