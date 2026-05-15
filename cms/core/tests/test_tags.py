from django.conf import settings
from django.test import RequestFactory, TestCase, override_settings
from wagtail.coreutils import get_dummy_request
from wagtail.models import Locale, Site

from cms.core.templatetags.page_config_tags import (
    _strip_locale_prefix,
    get_hreflangs,
    get_page_config,
    get_translation_urls,
)
from cms.core.templatetags.util_tags import (
    extend,
)
from cms.home.models import HomePage


class LocaleURLLookupMixin:
    """Helpers for looking up language switcher URLs by locale, independent of list order."""

    def _get_url_by_iso(self, urls, iso_code):
        """Look up a translation URL entry by ISO code."""
        return next(u for u in urls if u["isoCode"] == iso_code)

    def _get_hreflang_by_lang(self, hreflangs, lang):
        """Look up a hreflang entry by language code."""
        return next(h for h in hreflangs if h["lang"] == lang)


@override_settings(CMS_USE_SUBDOMAIN_LOCALES=False)
class LanguageTemplateTagTests(LocaleURLLookupMixin, TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.page = HomePage.objects.first()

    def setUp(self):
        self.dummy_request = get_dummy_request()

    def test_get_translation_urls(self):
        """Test that get_translation_urls returns the correct URLs."""
        # Call the function
        urls = get_translation_urls(self.dummy_request)

        self.assertIsInstance(urls, list)
        for url in urls:
            self.assertIn("url", url)
            self.assertIn("isoCode", url)
            self.assertIn("text", url)
            self.assertIn("current", url)

        en = self._get_url_by_iso(urls, "en")
        cy = self._get_url_by_iso(urls, "cy")
        self.assertEqual(en["url"], "/")
        self.assertEqual(en["text"], "English")
        self.assertEqual(en["current"], True)
        self.assertEqual(cy["current"], False)

    def test_get_hreflangs(self):
        """Test that get_hreflangs returns the correct hreflang URLs."""
        # Call the function
        hreflangs = get_hreflangs(self.dummy_request)

        self.assertIsInstance(hreflangs, list)
        self.assertEqual(len(hreflangs), 2)

        for hreflang in hreflangs:
            self.assertIn("url", hreflang)
            self.assertIn("lang", hreflang)

        en = self._get_hreflang_by_lang(hreflangs, "en-gb")
        cy = self._get_hreflang_by_lang(hreflangs, "cy")
        self.assertEqual(en["url"], "/")
        self.assertEqual(cy["url"], "/cy")

    @override_settings(
        LANGUAGE_CODE="pl",
        LANGUAGES=[("pl", "Polish"), ("cy", "Welsh")],
        WAGTAIL_CONTENT_LANGUAGES=[("pl", "Polish"), ("cy", "Welsh")],
    )
    def test_get_hreflangs_with_different_base_locale(self):
        """Test that get_hreflangs returns the correct hreflang URLs with a different base locale."""
        main_locale = Locale.objects.get(language_code="en-gb")
        main_locale.language_code = "pl"
        main_locale.save()

        # Call the function
        hreflangs = get_hreflangs(self.dummy_request)

        self.assertIsInstance(hreflangs, list)
        self.assertEqual(len(hreflangs), 2)

        for hreflang in hreflangs:
            self.assertIn("url", hreflang)
            self.assertIn("lang", hreflang)

        pl = self._get_hreflang_by_lang(hreflangs, "pl")
        cy = self._get_hreflang_by_lang(hreflangs, "cy")
        self.assertEqual(pl["url"], "/")
        self.assertEqual(cy["url"], "/cy")

    def test_translation_urls_preserve_sub_path(self):
        """Test that the language switcher preserves routable sub-paths."""
        request = get_dummy_request(path="/topic/articles/series/editions")
        urls = get_translation_urls(request)

        en = self._get_url_by_iso(urls, "en")
        cy = self._get_url_by_iso(urls, "cy")
        self.assertEqual(en["url"], "/topic/articles/series/editions")
        self.assertEqual(cy["url"], "/cy/topic/articles/series/editions")

    def test_translation_urls_preserve_sub_path_with_slug(self):
        """Test that the language switcher preserves edition slug sub-paths."""
        request = get_dummy_request(path="/topic/articles/series/editions/jan-2025")
        urls = get_translation_urls(request)

        en = self._get_url_by_iso(urls, "en")
        cy = self._get_url_by_iso(urls, "cy")
        self.assertEqual(en["url"], "/topic/articles/series/editions/jan-2025")
        self.assertEqual(cy["url"], "/cy/topic/articles/series/editions/jan-2025")

    def test_translation_urls_strip_welsh_prefix(self):
        """Test that Welsh prefix is correctly stripped and swapped."""
        request = get_dummy_request(path="/cy/topic/articles/series/editions")
        urls = get_translation_urls(request)

        en = self._get_url_by_iso(urls, "en")
        cy = self._get_url_by_iso(urls, "cy")
        self.assertEqual(en["url"], "/topic/articles/series/editions")
        self.assertEqual(cy["url"], "/cy/topic/articles/series/editions")

    def test_translation_urls_preserve_related_data_sub_path(self):
        """Test that the language switcher preserves related-data sub-paths."""
        request = get_dummy_request(path="/topic/articles/series/related-data")
        urls = get_translation_urls(request)

        en = self._get_url_by_iso(urls, "en")
        cy = self._get_url_by_iso(urls, "cy")
        self.assertEqual(en["url"], "/topic/articles/series/related-data")
        self.assertEqual(cy["url"], "/cy/topic/articles/series/related-data")

    def test_translation_urls_from_welsh_homepage(self):
        """Test that /cy (Welsh homepage) correctly maps back to / for English."""
        request = get_dummy_request(path="/cy")
        urls = get_translation_urls(request)

        en = self._get_url_by_iso(urls, "en")
        cy = self._get_url_by_iso(urls, "cy")
        self.assertEqual(en["url"], "/")
        self.assertEqual(cy["url"], "/cy")

    def test_caches_locale_urls_on_request(self):
        """Test that results are cached on the request object."""
        with self.assertNumQueries(1):  # Locale.objects.all()
            get_translation_urls(self.dummy_request)

        self.assertIsNotNone(getattr(self.dummy_request, "_locale_urls", None))

        # Second call should use the cache and issue no DB queries.
        with self.assertNumQueries(0):
            get_translation_urls(self.dummy_request)

    @override_settings(
        CMS_USE_SUBDOMAIN_LOCALES=True,
    )
    def test_caches_locale_urls_on_request_in_subdomain_mode(self):
        """Test that locale URLs are cached on the request object in subdomain mode."""
        # This test will behave the same way but for different reasons.
        with self.assertNumQueries(2):  # Locale.objects.all() and get_mapped_site_root_paths()
            get_translation_urls(self.dummy_request)

        self.assertIsNotNone(getattr(self.dummy_request, "_locale_urls", None))

        # Second call should still use the cache and issue no DB queries.
        with self.assertNumQueries(0):
            get_translation_urls(self.dummy_request)

    def test_hreflangs_preserve_sub_path(self):
        """Test that hreflangs also preserve routable sub-paths."""
        request = get_dummy_request(path="/topic/articles/series/editions")
        hreflangs = get_hreflangs(request)

        en = self._get_hreflang_by_lang(hreflangs, "en-gb")
        cy = self._get_hreflang_by_lang(hreflangs, "cy")
        self.assertEqual(en["url"], "/topic/articles/series/editions")
        self.assertEqual(cy["url"], "/cy/topic/articles/series/editions")


@override_settings(
    CMS_USE_SUBDOMAIN_LOCALES=True,
    CMS_HOSTNAME_LOCALE_MAP={
        "ons.localhost": "en-gb",
        "pub.ons.localhost": "en-gb",
        "cy.ons.localhost": "cy",
        "cy.pub.ons.localhost": "cy",
    },
    CMS_HOSTNAME_ALTERNATIVES={"ons.localhost": "pub.ons.localhost", "cy.ons.localhost": "cy.pub.ons.localhost"},
)
class SubdomainLanguageTemplateTagTests(LocaleURLLookupMixin, TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.page = HomePage.objects.first()

        cls.english_site = Site.objects.get(is_default_site=True)
        cls.english_site.hostname = "ons.localhost"
        cls.english_site.port = 80
        cls.english_site.save(update_fields=["hostname", "port"])

        cls.welsh_home = cls.page.aliases.first()
        cls.welsh_site = Site.objects.get(root_page=cls.welsh_home)
        cls.welsh_site.hostname = "cy.ons.localhost"
        cls.welsh_site.port = 80
        cls.welsh_site.save(update_fields=["hostname", "port"])

    def _make_request(self, hostname, path="/"):
        return RequestFactory(SERVER_NAME=hostname).get(path, SERVER_PORT=80)

    def test_translation_urls_from_english_domain(self):
        """Test URLs generated when on the English subdomain."""
        request = self._make_request("ons.localhost")
        urls = get_translation_urls(request)

        en = self._get_url_by_iso(urls, "en")
        cy = self._get_url_by_iso(urls, "cy")
        self.assertEqual(en["url"], "http://ons.localhost/")
        self.assertEqual(cy["url"], "http://cy.ons.localhost/")

    def test_translation_urls_preserve_sub_path(self):
        """Test that subdomain mode preserves routable sub-paths."""
        request = self._make_request("ons.localhost", path="/topic/articles/series/editions")
        urls = get_translation_urls(request)

        en = self._get_url_by_iso(urls, "en")
        cy = self._get_url_by_iso(urls, "cy")
        self.assertEqual(en["url"], "http://ons.localhost/topic/articles/series/editions")
        self.assertEqual(cy["url"], "http://cy.ons.localhost/topic/articles/series/editions")

    def test_translation_urls_from_welsh_domain(self):
        """Test that switching from Welsh domain preserves the path."""
        request = self._make_request("cy.ons.localhost", path="/topic/articles/series/editions")
        urls = get_translation_urls(request)

        en = self._get_url_by_iso(urls, "en")
        cy = self._get_url_by_iso(urls, "cy")
        self.assertEqual(en["url"], "http://ons.localhost/topic/articles/series/editions")
        self.assertEqual(cy["url"], "http://cy.ons.localhost/topic/articles/series/editions")

    def test_hreflangs_preserve_sub_path(self):
        """Test that subdomain hreflangs preserve routable sub-paths."""
        request = self._make_request("ons.localhost", path="/topic/articles/series/editions")
        hreflangs = get_hreflangs(request)

        en = self._get_hreflang_by_lang(hreflangs, "en-gb")
        cy = self._get_hreflang_by_lang(hreflangs, "cy")
        self.assertEqual(en["url"], "http://ons.localhost/topic/articles/series/editions")
        self.assertEqual(cy["url"], "http://cy.ons.localhost/topic/articles/series/editions")


@override_settings(CMS_USE_SUBDOMAIN_LOCALES=False)
class StripLocalePrefixTests(TestCase):
    def test_strips_welsh_prefix(self):
        self.assertEqual(_strip_locale_prefix("/cy/topic/articles"), "/topic/articles")

    def test_strips_welsh_prefix_root(self):
        self.assertEqual(_strip_locale_prefix("/cy"), "/")

    def test_no_prefix_unchanged(self):
        self.assertEqual(_strip_locale_prefix("/topic/articles"), "/topic/articles")

    def test_root_path_unchanged(self):
        self.assertEqual(_strip_locale_prefix("/"), "/")

    def test_strips_default_locale_prefix(self):
        """Test that the default locale prefix (en-gb) is also stripped."""
        self.assertEqual(_strip_locale_prefix("/en-gb/topic/articles"), "/topic/articles")

    def test_does_not_strip_partial_match(self):
        """Ensure /cyber/path is not confused with /cy/ber/path."""
        self.assertEqual(_strip_locale_prefix("/cyber/path"), "/cyber/path")


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
        self.request = get_dummy_request(site=Site.objects.get(hostname="ons.localhost"))
        self.request.LANGUAGE_CODE = settings.LANGUAGE_CODE

        self.welsh_request = get_dummy_request(site=Site.objects.get(hostname="cy.ons.localhost"))
        self.welsh_request.LANGUAGE_CODE = "cy"

    def test_page_config(self):
        config = get_page_config({"page": self.page, "request": self.request})

        self.assertEqual(config["bodyClasses"], "template-home-page")
        self.assertEqual(config["title"], f"Office for National Statistics - {self.page.title}")
        self.assertEqual(config["meta"]["canonicalUrl"], "https://ons.localhost/")
        self.assertEqual(config["absoluteUrl"], "http://ons.localhost:443/")

        self.assertEqual(
            config["header"]["search"],
            {"id": "search", "form": {"action": "/search", "inputName": "q"}},
        )

    def test_welsh_page_config(self):
        config = get_page_config({"page": self.welsh_home_page, "request": self.welsh_request})

        self.assertEqual(config["bodyClasses"], "template-home-page")
        self.assertEqual(config["title"], f"Swyddfa Ystadegau Gwladol - {self.welsh_home_page.title}")
        self.assertEqual(config["meta"]["canonicalUrl"], "https://cy.ons.localhost/")
        self.assertEqual(config["absoluteUrl"], "http://cy.ons.localhost:443/")

        self.assertEqual(
            config["header"]["search"],
            {"id": "search", "form": {"action": "/search", "inputName": "q"}},
        )

    def test_page_title_from_context_overrides_model(self):
        config = get_page_config({"page": self.page, "request": self.request, "page_title": "custom title"})
        self.assertEqual(config["title"], "Office for National Statistics - custom title")

    def test_config_no_page(self):
        with self.assertNumQueries(6):
            config = get_page_config({"request": self.request, "page_title": "not found"})

        self.assertEqual(config["bodyClasses"], "")
        self.assertEqual(config["title"], "not found - Office for National Statistics")
        self.assertEqual(len(config["header"]["language"]["languages"]), 2)
        self.assertEqual(config["meta"]["canonicalUrl"], "http://ons.localhost:443/")
        self.assertEqual(len(config["meta"]["hrefLangs"]), 2)
        self.assertEqual(config["absoluteUrl"], "http://ons.localhost:443/")

    @override_settings(
        CACHES={
            "default": {
                "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
                "LOCATION": "test_served_from_cache",
            }
        }
    )
    def test_served_from_cache(self):
        with self.assertNumQueries(6):
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
        with self.assertNumQueries(6):
            get_page_config({"page_title": "not found", "request": self.request})

        with self.assertNumQueries(0):
            get_page_config({"page_title": "not found", "request": self.request})

        # Recreate request so any on-object caches are cleared
        self.setUp()

        with self.assertNumQueries(2):
            get_page_config({"page_title": "not found", "request": self.request})
