from unittest.mock import patch

from django.test import TestCase, override_settings
from wagtail.models import Locale, Site, SiteRootPath

from cms.home.models import HomePage
from cms.locale.utils import get_mapped_site_root_paths, replace_hostname


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
class LocaleUtilsTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.en_locale = Locale.get_default()
        cls.welsh_locale = Locale.objects.get(language_code="cy")

        cls.home = HomePage.objects.first()
        cls.welsh_home = cls.home.aliases.first()

        cls.english_site = Site.objects.get(is_default_site=True)
        cls.english_site.hostname = "ons.localhost"
        cls.english_site.port = 80
        cls.english_site.save(update_fields=["hostname", "port"])
        cls.welsh_site = Site.objects.get(root_page=cls.welsh_home)
        cls.welsh_site.hostname = "cy.ons.localhost"
        cls.welsh_site.port = 80
        cls.welsh_site.save(update_fields=["hostname", "port"])

    def test_replace_hostname(self):
        # Test with URL that has no hostname
        result = replace_hostname("/page/")
        self.assertEqual(result, "/page/")

        # Test when no alternative hostname is configured
        result = replace_hostname("https://ons.gov.uk/")
        self.assertEqual(result, "https://ons.gov.uk/")

        # Test when alternative is configured and hostname replacement occurs
        result = replace_hostname("https://ons.localhost/page/")
        self.assertEqual(result, "https://pub.ons.localhost/page/")

        result = replace_hostname("https://ons.localhost:8080/")
        self.assertEqual(result, "https://pub.ons.localhost:8080/")

        # Test when alternative is the same as current hostname (no replacement)
        with override_settings(CMS_HOSTNAME_ALTERNATIVES={"ons.localhost": "ons.localhost"}):
            result = replace_hostname("https://ons.localhost/page/")
            self.assertEqual(result, "https://ons.localhost/page/")

    def test_get_mapped_site_root_paths(self):
        default_expected = [
            SiteRootPath(
                site_id=self.welsh_site.pk,
                root_path=self.welsh_site.root_page.url_path,
                root_url=self.welsh_site.root_url,
                language_code=self.welsh_locale.language_code,
            ),
            SiteRootPath(
                site_id=self.english_site.pk,
                root_path=self.english_site.root_page.url_path,
                root_url=self.english_site.root_url,
                language_code=self.en_locale.language_code,
            ),
        ]
        self.assertEqual(get_mapped_site_root_paths(), default_expected)
        self.assertEqual(get_mapped_site_root_paths("foo.bar"), default_expected)

        self.assertEqual(
            get_mapped_site_root_paths(host="pub.ons.localhost"),
            [
                SiteRootPath(
                    site_id=self.welsh_site.pk,
                    root_path=self.welsh_site.root_page.url_path,
                    root_url="http://cy.pub.ons.localhost",
                    language_code=self.welsh_locale.language_code,
                ),
                SiteRootPath(
                    site_id=self.english_site.pk,
                    root_path=self.english_site.root_page.url_path,
                    root_url="http://pub.ons.localhost",
                    language_code=self.en_locale.language_code,
                ),
            ],
        )

    @patch("cms.locale.utils.cache.get")
    @patch("cms.locale.utils.cache.set")
    def test_get_mapped_site_root_paths_caches_results(self, mock_cache_set, mock_cache_get):
        get_mapped_site_root_paths()
        mock_cache_set.assert_not_called()

        mock_cache_get.return_value = None
        get_mapped_site_root_paths()

        mock_cache_set.assert_called_once()
