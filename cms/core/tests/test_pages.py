import json
from http import HTTPStatus

from bs4 import BeautifulSoup
from wagtail.test.utils import WagtailPageTestCase

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
        response = self.client.get(self.page.url)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertContains(response, f'<link rel="canonical" href="http://testserver{self.page.url}" />')

    def test_welsh_page_alias_canonical_url(self):
        """Test that the Welsh home page has the correct english canonical URL
        when it has not been explicitly translated.
        """
        response = self.client.get(f"/cy{self.page.url}")
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertContains(response, f'<link rel="canonical" href="http://testserver{self.page.url}" />')


class PageSchemaOrgTests(WagtailPageTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.index_page = IndexPageFactory()
        cls.page = InformationPageFactory(parent=cls.index_page)

    def test_schema_org_home_page(self):
        """Test that the page has the correct schema.org markup."""
        response = self.client.get("/")
        self.assertEqual(response.status_code, HTTPStatus.OK)

        self.assertContains(response, '<script type="application/ld+json">')

        soup = BeautifulSoup(response.content, "html.parser")
        jsonld_scripts = soup.find_all("script", {"type": "application/ld+json"})
        self.assertEqual(len(jsonld_scripts), 1)

        actual_jsonld = json.loads(jsonld_scripts[0].string)
        self.assertEqual(actual_jsonld["@context"], "http://schema.org")
        self.assertEqual(actual_jsonld["@type"], "WebPage")
        self.assertEqual(actual_jsonld["name"], "Home")
        self.assertEqual(actual_jsonld["url"], "http://localhost/")
        self.assertEqual(actual_jsonld["@id"], "http://localhost/")
        self.assertNotIn("breadcrumb", actual_jsonld, "The home should not have breadcrumbs")

    def test_page_schema_org_with_breadcrumbs(self):
        """Test that the page has the correct schema.org markup including breadcrumbs."""
        response = self.client.get(self.page.url)
        self.assertEqual(response.status_code, HTTPStatus.OK)

        self.assertContains(response, '<script type="application/ld+json">')

        soup = BeautifulSoup(response.content, "html.parser")
        jsonld_scripts = soup.find_all("script", {"type": "application/ld+json"})
        self.assertEqual(len(jsonld_scripts), 1)

        actual_jsonld = json.loads(jsonld_scripts[0].string)
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
        self.assertEqual(breadcrumbs[0]["item"], "http://localhost/")
        self.assertEqual(breadcrumbs[0]["name"], "Home")
        self.assertEqual(breadcrumbs[0]["@type"], "ListItem")
        self.assertEqual(breadcrumbs[0]["position"], 1)
        self.assertEqual(breadcrumbs[1]["item"], self.index_page.get_full_url(request=self.dummy_request))
        self.assertEqual(breadcrumbs[1]["name"], self.index_page.title)
        self.assertEqual(breadcrumbs[1]["@type"], "ListItem")
        self.assertEqual(breadcrumbs[1]["position"], 2)
