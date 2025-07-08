from http import HTTPStatus

from django.conf import settings
from wagtail.models import Locale
from wagtail.test.utils import WagtailPageTestCase

from cms.core.tests.utils import extract_response_jsonld
from cms.standard_pages.tests.factories import IndexPageFactory, InformationPageFactory


class HomePageTests(WagtailPageTestCase):
    def test_home_page_can_be_served(self):
        """Test that the home page can be served."""
        response = self.client.get("/")
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_home_page_template(self):
        response = self.client.get("/")
        self.assertContains(response, "This is a new service")
        self.assertContains(response, "All content is available under the")

    def test_welsh_home_page_can_be_served(self):
        response = self.client.get("/cy/")
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_unsupported_language_home_page_is_not_found(self):
        response = self.client.get("/fr/")
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    def test_welsh_home_page_template(self):
        response = self.client.get("/cy/")
        self.assertContains(response, "Mae'r holl gynnwys ar gael o dan delerau'r")


class PageCanonicalUrlTests(WagtailPageTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.page = InformationPageFactory()

    def test_page_canonical_url(self):
        """Test that the home page has the correct canonical URL."""
        response = self.client.get(self.page.get_url(request=self.dummy_request))
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertContains(
            response, f'<link rel="canonical" href="{self.page.get_full_url(request=self.dummy_request)}" />'
        )

    def test_welsh_page_alias_canonical_url(self):
        """Test that the Welsh home page has the correct english canonical URL
        when it has not been explicitly translated.
        """
        response = self.client.get(f"/cy{self.page.get_url(request=self.dummy_request)}")
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertContains(
            response, f'<link rel="canonical" href="{self.page.get_full_url(request=self.dummy_request)}" />'
        )

    def test_translated_page_canonical_url(self):
        """Test that a translated page has the correct language coded canonical URL."""
        cy_locale = Locale.objects.get(language_code="cy")
        for page_ancestor in self.page.get_ancestors()[1:]:
            translated_page = page_ancestor.copy_for_translation(locale=cy_locale)
            translated_page.save_revision().publish()

        welsh_page = self.page.copy_for_translation(locale=cy_locale)
        welsh_page.save_revision().publish()
        response = self.client.get(welsh_page.get_url())
        self.assertEqual(response.status_code, HTTPStatus.OK)

        self.assertIn(welsh_page.get_site().root_url + "/cy/", welsh_page.get_full_url())
        self.assertContains(response, f'<link rel="canonical" href="{welsh_page.get_full_url()}" />')


class PageSchemaOrgTests(WagtailPageTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.index_page = IndexPageFactory()
        cls.page = InformationPageFactory(parent=cls.index_page)

    def test_schema_org_data_home_page(self):
        """Test that the page has the correct schema.org markup."""
        response = self.client.get("/")
        self.assertEqual(response.status_code, HTTPStatus.OK)

        actual_jsonld = extract_response_jsonld(response.content, self)

        self.assertEqual(actual_jsonld["@context"], "http://schema.org")
        self.assertEqual(actual_jsonld["@type"], "WebPage")
        self.assertEqual(actual_jsonld["name"], "Home")
        self.assertEqual(actual_jsonld["url"], self.page.get_site().root_url + "/")
        self.assertEqual(actual_jsonld["@id"], self.page.get_site().root_url + "/")
        self.assertNotIn("breadcrumb", actual_jsonld, "The home page should not have breadcrumbs")

    def test_schema_org_data_with_breadcrumbs(self):
        """Test that the page has the correct schema.org markup including breadcrumbs."""
        response = self.client.get(self.page.get_url(request=self.dummy_request))
        self.assertEqual(response.status_code, HTTPStatus.OK)

        actual_jsonld = extract_response_jsonld(response.content, self)

        self.assertEqual(actual_jsonld["@context"], "http://schema.org")
        self.assertEqual(actual_jsonld["@type"], "WebPage")
        self.assertEqual(actual_jsonld["name"], self.page.title)
        self.assertEqual(actual_jsonld["url"], self.page.get_full_url(request=self.dummy_request))
        self.assertEqual(actual_jsonld["@id"], self.page.get_full_url(request=self.dummy_request))
        self.assertEqual(actual_jsonld["description"], self.page.search_description)

        actual_jsonld_breadcrumbs = actual_jsonld.get("breadcrumb")
        self.assertIsNotNone(actual_jsonld_breadcrumbs)
        self.assertEqual(actual_jsonld_breadcrumbs["@type"], "BreadcrumbList")
        breadcrumbs = actual_jsonld_breadcrumbs["itemListElement"]
        self.assertEqual(len(breadcrumbs), 2)
        self.assertEqual(breadcrumbs[0]["item"], self.page.get_site().root_url)
        self.assertEqual(breadcrumbs[0]["name"], "Home")
        self.assertEqual(breadcrumbs[0]["@type"], "ListItem")
        self.assertEqual(breadcrumbs[0]["position"], 1)
        self.assertEqual(breadcrumbs[1]["item"], self.index_page.get_full_url(request=self.dummy_request))
        self.assertEqual(breadcrumbs[1]["name"], self.index_page.title)
        self.assertEqual(breadcrumbs[1]["@type"], "ListItem")
        self.assertEqual(breadcrumbs[1]["position"], 2)

    def test_schema_org_description(self):
        """Test the schema.org headline uses the search_description by default, falling back to listing_summary."""
        description_cases = [
            {
                "search_description": "Search description",
                "listing_summary": "Listing summary",
                "expected_description": "Search description",
            },
            {
                "search_description": "",
                "listing_summary": "Listing summary",
                "expected_description": "Listing summary",
            },
        ]

        for description_case in description_cases:
            with self.subTest(description_case=description_case):
                self.page.search_description = description_case["search_description"]
                self.page.listing_summary = description_case["listing_summary"]
                self.page.save_revision().publish()

                response = self.client.get(self.page.get_url(request=self.dummy_request))
                self.assertEqual(response.status_code, HTTPStatus.OK)
                actual_jsonld = extract_response_jsonld(response.content, self)

                self.assertEqual(actual_jsonld["description"], description_case["expected_description"])


class SocialMetaTests(WagtailPageTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.page = InformationPageFactory()

    def test_social_meta_image_fallback(self):
        """Test that the image meta tag falls back to the ONS logo from the CDN."""
        response = self.client.get(self.page.get_url(request=self.dummy_request))
        self.assertEqual(response.status_code, HTTPStatus.OK)

        self.assertContains(
            response,
            f'<meta property="og:image" content="{settings.FALLBACK_OG_IMAGE_URL}" />',
        )
