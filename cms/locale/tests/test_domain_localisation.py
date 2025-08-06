from django.test import RequestFactory, override_settings
from django.utils import translation
from wagtail.coreutils import get_dummy_request
from wagtail.models import Locale, Site
from wagtail.test.utils import WagtailPageTestCase
from wagtail_factories import SiteFactory

from cms.home.models import HomePage
from cms.standard_pages.tests.factories import InformationPageFactory


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
class SubdomainLocalisationTests(WagtailPageTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.en_locale = Locale.get_default()
        cls.welsh_locale = Locale.objects.get(language_code="cy")

        cls.home = HomePage.objects.first()
        cls.welsh_home = cls.home.copy_for_translation(cls.welsh_locale, alias=True)

        cls.english_site = Site.objects.get()
        cls.english_site.hostname = "ons.localhost"
        cls.english_site.root_page = cls.home
        cls.english_site.save(update_fields=["hostname"])
        cls.welsh_site = SiteFactory(hostname="cy.ons.localhost", port=80, root_page=cls.welsh_home)

        cls.page = InformationPageFactory(parent=cls.home, slug="about")
        cls.welsh_page = cls.page.copy_for_translation(cls.welsh_locale, alias=True)

    def setUp(self):
        self.dummy_request = get_dummy_request()

    def tearDown(self):
        # Clear translation caches
        translation.deactivate()

    def test_full_url(self):
        self.assertEqual(self.page.get_full_url(request=self.dummy_request), "http://ons.localhost/about/")
        self.assertEqual(self.welsh_page.get_full_url(request=self.dummy_request), "http://cy.ons.localhost/about/")

    def test_full_url_from_alternate_domains(self):
        request = RequestFactory(SERVER_NAME="pub.ons.localhost").get("/", SERVER_PORT=80)
        self.assertEqual(self.page.get_full_url(request=request), "http://pub.ons.localhost/about/")
        self.assertEqual(self.welsh_page.get_full_url(request=request), "http://cy.pub.ons.localhost/about/")

    def test_full_url_from_alternate_domains_not_in_mapping(self):
        request = RequestFactory(SERVER_NAME="foo.ons.localhost").get("/", SERVER_PORT=80)
        self.assertEqual(self.page.get_full_url(request=request), "http://ons.localhost/about/")
        self.assertEqual(self.welsh_page.get_full_url(request=request), "http://cy.ons.localhost/about/")

    def test_accessing_welsh_subdomain_activates_welsh(self):
        translation.deactivate()
        request = RequestFactory(SERVER_NAME="cy.ons.localhost").get("/", SERVER_PORT=80)
        response = self.client.get(self.welsh_page.get_full_url(request=request), headers={"host": "cy.ons.localhost"})
        self.assertEqual(translation.get_language(), self.welsh_locale.language_code)
        self.assertContains(response, "Mae'r holl gynnwys ar gael o dan delerau'r")

    def test_accessing_welsh_alternate_domain_activates_welsh(self):
        translation.deactivate()
        request = RequestFactory(SERVER_NAME="cy.pub.ons.localhost").get("/", SERVER_PORT=80)
        response = self.client.get(
            self.welsh_page.get_full_url(request=request), headers={"host": "cy.pub.ons.localhost"}
        )
        self.assertEqual(translation.get_language(), self.welsh_locale.language_code)
        self.assertContains(response, "Mae'r holl gynnwys ar gael o dan delerau'r")
