from http import HTTPStatus
from unittest.mock import patch

from django.conf import settings
from django.template import TemplateDoesNotExist
from django.template.loader import get_template as original_get_template
from django.test.utils import override_settings
from django.utils import translation
from wagtail.coreutils import get_dummy_request
from wagtail.models import Locale
from wagtail.test.utils import WagtailPageTestCase

from cms.core.tests.utils import extract_datalayer_pushed_values, extract_response_jsonld
from cms.home.models import HomePage
from cms.standard_pages.tests.factories import IndexPageFactory, InformationPageFactory


class HomePageTests(WagtailPageTestCase):
    def setUp(self):
        self.page = HomePage.objects.first()

    def tearDown(self):
        # Reset the translation to the default language after each test to avoid
        # test contamination issues.
        translation.activate(settings.LANGUAGE_CODE)
        return super().tearDown()

    def test_home_page_can_be_served(self):
        """Test that the home page can be served."""
        response = self.client.get("/")
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_home_page_template(self):
        response = self.client.get("/")
        self.assertContains(response, "This is a new service")
        self.assertContains(response, "All content is available under the")

    def test_welsh_home_page_can_be_served(self):
        response = self.client.get("/cy")
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_unsupported_language_home_page_is_not_found(self):
        response = self.client.get("/fr")
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    def test_welsh_home_page_template(self):
        response = self.client.get("/cy")
        self.assertContains(response, "Mae’r holl gynnwys ar gael o dan y")

    @override_settings(IS_EXTERNAL_ENV=False, WAGTAIL_CORE_ADMIN_LOGIN_ENABLED=True, AWS_COGNITO_LOGIN_ENABLED=True)
    def test_both_login_buttons_are_displayed(self):
        response = self.client.get("/")
        self.assertContains(response, "To access the administrative interface, please use the following option(s):")
        self.assertContains(response, "Wagtail Core Default Login")
        self.assertContains(response, 'href="/admin/login/"')
        self.assertContains(response, "Florence Login")
        self.assertContains(response, 'href="/admin/"')

    @override_settings(IS_EXTERNAL_ENV=False, WAGTAIL_CORE_ADMIN_LOGIN_ENABLED=True, AWS_COGNITO_LOGIN_ENABLED=False)
    def test_only_core_login_button_is_displayed(self):
        response = self.client.get("/")
        self.assertContains(response, "To access the administrative interface, please use the following option(s):")
        self.assertContains(response, "Wagtail Core Default Login")
        self.assertContains(response, 'href="/admin/login/"')
        self.assertNotContains(response, "Florence Login")

    @override_settings(IS_EXTERNAL_ENV=False, WAGTAIL_CORE_ADMIN_LOGIN_ENABLED=False, AWS_COGNITO_LOGIN_ENABLED=True)
    def test_only_cognito_login_button_is_displayed(self):
        response = self.client.get("/")
        self.assertContains(response, "To access the administrative interface, please use the following option(s):")
        self.assertContains(response, "Florence Login")
        self.assertContains(response, 'href="/admin/"')
        self.assertNotContains(response, "Wagtail Core Default Login")

    @override_settings(IS_EXTERNAL_ENV=True, WAGTAIL_CORE_ADMIN_LOGIN_ENABLED=True, AWS_COGNITO_LOGIN_ENABLED=True)
    def test_no_buttons_in_external_environment(self):
        response = self.client.get("/")
        # The prompt and buttons should be omitted entirely
        self.assertNotContains(response, "To access the administrative interface, please use the following option(s):")
        self.assertNotContains(response, "Wagtail Core Default Login")
        self.assertNotContains(response, "Florence Login")

    def test_page_analytics_values(self):
        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)

        datalayer_values = extract_datalayer_pushed_values(response.text)
        self.assertEqual(datalayer_values["product"], "wagtail")
        self.assertEqual(datalayer_values["gtm.allowlist"], ["google", "hjtc", "lcl"])
        self.assertEqual(datalayer_values["gtm.blocklist"], ["customScripts", "sp", "adm", "awct", "k", "d", "j"])
        for key, value in self.page.get_analytics_values(get_dummy_request(path="/")).items():
            self.assertIn(key, datalayer_values)
            self.assertEqual(datalayer_values[key], value)

    @override_settings(GOOGLE_TAG_MANAGER_CONTAINER_ID="")
    def test_page_analytics_values_disabled(self):
        """Test that no analytics values are pushed to the datalayer when GTM is not configured."""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(extract_datalayer_pushed_values(response.text)), 0)

    def test_language_toggle_welsh_link(self):
        """Test that the Welsh language toggle link is present on the English home page."""
        response = self.client.get("/")
        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.content.decode(encoding="utf-8")
        self.assertInHTML(
            ('<a href="/cy" lang="cy"><span class="ons-u-vh">Change language to </span>Cymraeg</a>'), content
        )

    def test_language_toggle_english_link(self):
        """Test that the English language toggle link is present on the Welsh home page."""
        response = self.client.get("/cy")
        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.content.decode(encoding="utf-8")
        self.assertInHTML(
            ('<a href="/" lang="en"><span class="ons-u-vh">Change language to </span>English</a>'), content
        )


class PageCanonicalUrlTests(WagtailPageTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.page = InformationPageFactory()

    def tearDown(self):
        # Reset the translation to the default language after each test to avoid
        # test contamination issues.
        translation.activate(settings.LANGUAGE_CODE)
        return super().tearDown()

    def test_page_canonical_url(self):
        """Test that the home page has the correct canonical URL."""
        response = self.client.get(self.page.get_url(request=self.dummy_request))
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertContains(
            response, f'<link rel="canonical" href="{self.page.get_full_url(request=self.dummy_request)}" />'
        )

    def test_welsh_page_alias_canonical_url(self):
        """Test that the a welsh page has the correct english canonical URL when it has not been explicitly
        translated.
        """
        self.page.copy_for_translation(locale=Locale.objects.get(language_code="cy"), copy_parents=True, alias=True)
        response = self.client.get(f"/cy{self.page.get_url(request=self.dummy_request)}")
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertContains(
            response, f'<link rel="canonical" href="{self.page.get_full_url(request=self.dummy_request)}" />'
        )

    def test_translated_page_canonical_url(self):
        """Test that a translated page has the correct language coded canonical URL."""
        welsh_page = self.page.copy_for_translation(locale=Locale.objects.get(language_code="cy"), copy_parents=True)
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
            f'<meta property="og:image" content="{settings.DEFAULT_OG_IMAGE_URL}" />',
        )


class ErrorPageTests(WagtailPageTestCase):
    def tearDown(self):
        # Reset the translation to the default language after each test to avoid
        # test contamination issues.
        translation.activate(settings.LANGUAGE_CODE)
        return super().tearDown()

    def get_template_side_effect(self, template_name, *args, **kwargs):
        """Side effect function to simulate template loading failures."""
        if template_name == "templates/pages/errors/500.html":
            raise TemplateDoesNotExist("Forced failure to find primary 500 template")

        # For any other template (like our fallback), use the real get_template function
        return original_get_template(template_name, *args, **kwargs)

    def test_404_page(self):
        """Test that the 404 page can be served."""
        e404_urls = [
            "/non-existent-page",
            "/nested/non-existent-page",
            "/non-existent-page?with_query=string",
        ]
        for url in e404_urls:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)
                self.assertIn("Page not found", response.content.decode("utf-8"))
                self.assertIn("If you entered a web address, check it is correct.", response.content.decode("utf-8"))

    def test_301_before_404_page(self):
        """Test that a 301 redirect is returned before the 404 page is served when necessary."""
        # The lack of a trailing slash on the URL should result in a 301 redirect,
        # even if the page does not exist.
        response = self.client.get("/non-existent-page-with-trailing-slash/")
        self.assertEqual(response.status_code, HTTPStatus.MOVED_PERMANENTLY)

        # Follow the redirect
        response = self.client.get(response["Location"])
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)
        self.assertIn("Page not found", response.content.decode("utf-8"))
        self.assertIn("If you entered a web address, check it is correct.", response.content.decode("utf-8"))

    def test_404_page_uses_contact_us_setting(self):
        """Test that the 404 page uses the CONTACT_US_URL setting for the contact link."""
        response = self.client.get("/non-existent-page")
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)
        self.assertContains(response, f'href="{settings.CONTACT_US_URL}"', status_code=HTTPStatus.NOT_FOUND)

    @override_settings(CONTACT_US_URL="/custom/contact-path")
    def test_404_page_uses_custom_contact_us_setting(self):
        """Test that the 404 page uses a custom CONTACT_US_URL setting when configured."""
        response = self.client.get("/non-existent-page")
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)
        self.assertContains(response, 'href="/custom/contact-path"', status_code=HTTPStatus.NOT_FOUND)

    def test_404_page_analytics_values(self):
        response = self.client.get("/non-existent-page")
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)
        datalayer_values = extract_datalayer_pushed_values(response.text)
        self.assertEqual(datalayer_values["product"], "wagtail")
        self.assertEqual(datalayer_values["gtm.allowlist"], ["google", "hjtc", "lcl"])
        self.assertEqual(datalayer_values["gtm.blocklist"], ["customScripts", "sp", "adm", "awct", "k", "d", "j"])
        self.assertEqual(datalayer_values["contentType"], "404-pages")
        self.assertEqual(datalayer_values["contentGroup"], "404-pages")

    @patch("cms.home.models.HomePage.serve")
    def test_500_page(self, mock_homepage_serve):
        """Test that the 500 page can be served."""
        self.client.raise_request_exception = False

        # Mock the HomePage serve method to raise an exception, simulating something
        # going wrong in the view logic.
        mock_homepage_serve.side_effect = ValueError("Deliberate test error")

        response = self.client.get("/")

        self.assertEqual(response.status_code, HTTPStatus.INTERNAL_SERVER_ERROR)
        self.assertContains(
            response, "Sorry, there’s a problem with the service", status_code=HTTPStatus.INTERNAL_SERVER_ERROR
        )
        # This uses the base template, which has OG tags
        self.assertContains(response, 'property="og:description"', status_code=HTTPStatus.INTERNAL_SERVER_ERROR)

        # Rendering and translations should still work
        response = self.client.get("/cy")
        self.assertEqual(response.status_code, HTTPStatus.INTERNAL_SERVER_ERROR)
        self.assertContains(
            response, "Mae’n ddrwg gennym, mae problem gyda’r gwasanaeth", status_code=HTTPStatus.INTERNAL_SERVER_ERROR
        )

    @patch("cms.home.models.HomePage.serve")
    @patch("django.template.loader.get_template")
    def test_500_primary_fallback(self, mock_get_template, mock_homepage_serve):
        """Test that the 500 page falls back to a basic HTML response."""
        self.client.raise_request_exception = False
        mock_homepage_serve.side_effect = ValueError("Deliberate test error")
        # The side effect will raise TemplateDoesNotExist for the primary 500 template, but in general
        # any issue with rendering the main 500 template should trigger the fallback.
        mock_get_template.side_effect = self.get_template_side_effect

        response = self.client.get("/")
        self.assertEqual(response.status_code, HTTPStatus.INTERNAL_SERVER_ERROR)
        self.assertContains(
            response,
            "Sorry, there’s a problem with the service",
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
        )

        templates_called = [call.args[0] for call in mock_get_template.call_args_list]

        # Rendering still works, but it should have used the fallback template
        self.assertListEqual(
            templates_called, ["templates/pages/errors/500.html", "templates/pages/errors/500_fallback.html"]
        )

        # Check that the fallback template was actually used, it doesn't have OG tags like the base template
        self.assertNotContains(response, 'property="og:description"', status_code=HTTPStatus.INTERNAL_SERVER_ERROR)

        response = self.client.get("/cy")
        self.assertEqual(response.status_code, HTTPStatus.INTERNAL_SERVER_ERROR)

        # The fallback template does not have Welsh translations
        self.assertNotContains(
            response,
            "Mae’n ddrwg gennym, mae problem gyda’r gwasanaeth",
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
        )
        self.assertContains(
            response,
            "Sorry, there’s a problem with the service",
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
        )

    @patch("cms.home.models.HomePage.serve")
    @patch("cms.core.views.render")
    def test_500_final_fallback(self, mock_render, mock_homepage_serve):
        """Test that the 500 page falls back to a basic HTML response."""
        self.client.raise_request_exception = False
        mock_homepage_serve.side_effect = ValueError("Deliberate test error")
        # Mock the render function to raise an exception, so that no rendering works
        mock_render.side_effect = Exception("Deliberate render error")

        response = self.client.get("/")
        self.assertEqual(response.status_code, HTTPStatus.INTERNAL_SERVER_ERROR)
        # Rendering is not possible, so we return a plain HTML response
        self.assertContains(
            response,
            "<h1>Server Error (500)</h1><p>Sorry, there’s a problem with the service.</p>",
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
        )

        # Welsh version should also return a plain HTML response
        response = self.client.get("/cy")
        self.assertEqual(response.status_code, HTTPStatus.INTERNAL_SERVER_ERROR)
        self.assertContains(
            response,
            "<h1>Server Error (500)</h1><p>Sorry, there’s a problem with the service.</p>",
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
        )
