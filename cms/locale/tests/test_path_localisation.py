from http import HTTPStatus
from unittest.mock import patch

from django.template import TemplateDoesNotExist
from django.template.loader import get_template as original_get_template
from django.test import override_settings
from django.utils import translation
from wagtail.coreutils import get_dummy_request
from wagtail.models import Locale, Site
from wagtail.test.utils import WagtailPageTestCase

from cms.articles.tests.factories import ArticleSeriesPageFactory, StatisticalArticlePageFactory
from cms.core.tests.utils import reset_url_caches
from cms.standard_pages.tests.factories import InformationPageFactory


@override_settings(CMS_USE_SUBDOMAIN_LOCALES=False)
class PathBasedLocalisationTests(WagtailPageTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = cls.create_superuser("admin")
        cls.welsh_locale = Locale.objects.get(language_code="cy")

        cls.information_page = InformationPageFactory(title="The information page")
        cls.welsh_information_page_alias = cls.information_page.copy_for_translation(
            locale=cls.welsh_locale, copy_parents=True, alias=True
        )
        cls.article_series = ArticleSeriesPageFactory(title="PSF")
        cls.statistical_article_page = StatisticalArticlePageFactory(
            title="August 2025", parent=cls.article_series, summary="This is the summary"
        )
        cls.statistical_article_page.save_revision().publish()
        cls.welsh_article_page_alias = cls.statistical_article_page.copy_for_translation(
            locale=cls.welsh_locale, copy_parents=True, alias=True
        )

        # remove all but the default site
        Site.objects.filter(is_default_site=False).delete()

    def setUp(self):
        self.dummy_request = get_dummy_request()

        reset_url_caches()

    def tearDown(self):
        # Clear translation caches
        translation.deactivate()

        reset_url_caches()

    def get_template_side_effect(self, template_name, *args, **kwargs):
        """Side effect function to simulate template loading failures."""
        if template_name == "templates/pages/errors/500.html":
            raise TemplateDoesNotExist("Forced failure to find primary 500 template")

        # For any other template (like our fallback), use the real get_template function
        return original_get_template(template_name, *args, **kwargs)

    def test_urls(self):
        self.assertEqual(
            self.welsh_information_page_alias.get_url(request=self.dummy_request),
            f"/cy{self.information_page.get_url(request=self.dummy_request)}",
        )
        self.assertEqual(
            self.welsh_article_page_alias.get_url(request=self.dummy_request),
            f"/cy{self.statistical_article_page.get_url(request=self.dummy_request)}",
        )

    def test_welsh_home_page_can_be_served(self):
        response = self.client.get("/cy")
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(translation.get_language(), self.welsh_locale.language_code)
        self.assertContains(response, "Mae’r holl gynnwys ar gael o dan y")

    def test_localised_version_of_page_works(self):
        response = self.client.get(self.welsh_article_page_alias.get_url(request=self.dummy_request))
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(translation.get_language(), self.welsh_locale.language_code)

        # Body of the page is still English
        self.assertContains(response, self.statistical_article_page.title)
        self.assertContains(response, self.statistical_article_page.summary)

        # However, the page's furniture should be in Welsh
        self.assertContains(response, "Mae’r holl gynnwys ar gael o dan y")

    def test_unknown_localised_version_of_page_404(self):
        response = self.client.get("/fr" + self.statistical_article_page.url)
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    def test_welsh_page_alias_canonical_url(self):
        """Test that the Welsh page has the correct English canonical URL when it has not been explicitly
        translated.
        """
        response = self.client.get(self.welsh_information_page_alias.get_url(request=self.dummy_request))
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertContains(
            response,
            f'<link rel="canonical" href="{self.information_page.get_full_url(request=self.dummy_request)}" />',
        )

    def test_translated_page_canonical_url(self):
        """Test that a translated page has the correct language coded canonical URL."""
        welsh_page = self.welsh_information_page_alias
        welsh_page.alias_of = None
        welsh_page.save_revision().publish()
        response = self.client.get(welsh_page.get_url())
        self.assertEqual(response.status_code, HTTPStatus.OK)

        self.assertIn(welsh_page.get_site().root_url + "/cy/", welsh_page.get_full_url())
        self.assertContains(response, f'<link rel="canonical" href="{welsh_page.get_full_url()}" />')

    def test_aliased_welsh_statistical_article_page_canonical_url(self):
        """Test that Welsh articles have the correct english canonical URL when they have not been explicitly
        translated.
        """
        response = self.client.get(self.welsh_article_page_alias.get_url(request=self.dummy_request))
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertContains(
            response, f'<link rel="canonical" href="{self.article_series.get_full_url(request=self.dummy_request)}" />'
        )
        self.client.get({self.statistical_article_page.get_url(request=self.dummy_request)})

    def test_translated_welsh_statistical_article_page_canonical_url(self):
        """Test that a translated article has the correct language coded canonical URL."""
        welsh_page = self.welsh_article_page_alias
        welsh_page.alias_of = None
        welsh_page.save_revision().publish()
        response = self.client.get(welsh_page.get_url(request=self.dummy_request))
        self.assertEqual(response.status_code, HTTPStatus.OK)
        welsh_series_url = welsh_page.get_parent().get_full_url(request=self.dummy_request)
        self.assertIn(welsh_page.get_site().root_url + "/cy/", welsh_series_url)
        self.assertContains(response, f'<link rel="canonical" href="{welsh_series_url}" />')

    @patch("cms.home.models.HomePage.serve")
    def test_500_page(self, mock_homepage_serve):
        """Test that the 500 page can be served."""
        self.client.raise_request_exception = False

        # Mock the HomePage serve method to raise an exception, simulating something
        # going wrong in the view logic.
        mock_homepage_serve.side_effect = ValueError("Deliberate test error")

        response = self.client.get("/cy")
        self.assertEqual(response.status_code, HTTPStatus.INTERNAL_SERVER_ERROR)
        self.assertNotContains(
            response, "Sorry, there’s a problem with the service", status_code=HTTPStatus.INTERNAL_SERVER_ERROR
        )
        # This uses the base template, which has OG tags
        self.assertContains(response, 'property="og:description"', status_code=HTTPStatus.INTERNAL_SERVER_ERROR)
        self.assertContains(
            response, "Mae’n ddrwg gennym, mae problem gyda’r gwasanaeth", status_code=HTTPStatus.INTERNAL_SERVER_ERROR
        )

    @patch("cms.home.models.HomePage.serve")
    @patch("django.template.loader.get_template")
    def test_500_primary_fallback(self, mock_get_template, mock_homepage_serve):
        """Test that if the primary 500 error template ('500.html') cannot be loaded, we fall back to rendering
        the '500_fallback.html' template.
        """
        self.client.raise_request_exception = False
        mock_homepage_serve.side_effect = ValueError("Deliberate test error")
        # The side effect will raise TemplateDoesNotExist for the primary 500 template, but in general
        # any issue with rendering the main 500 template should trigger the fallback.
        mock_get_template.side_effect = self.get_template_side_effect

        response = self.client.get("/cy")
        self.assertEqual(response.status_code, HTTPStatus.INTERNAL_SERVER_ERROR)

        templates_called = [call.args[0] for call in mock_get_template.call_args_list]

        # Rendering still works, but it should have used the fallback template
        self.assertListEqual(
            templates_called, ["templates/pages/errors/500.html", "templates/pages/errors/500_fallback.html"]
        )

        # Check that the fallback template was actually used, it doesn't have OG tags like the base template
        self.assertNotContains(response, 'property="og:description"', status_code=HTTPStatus.INTERNAL_SERVER_ERROR)

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
    def test_500_fallback(self, mock_render, mock_homepage_serve):
        """Test that if all template rendering fails (including the fallback template), the system returns a plain,
        hardcoded HTML error response for a 500 error.
        """
        self.client.raise_request_exception = False
        mock_homepage_serve.side_effect = ValueError("Deliberate test error")
        # Mock the render function to raise an exception, so that no rendering works
        mock_render.side_effect = Exception("Deliberate render error")

        # Welsh version should return a plain HTML response
        response = self.client.get("/cy")
        self.assertEqual(response.status_code, HTTPStatus.INTERNAL_SERVER_ERROR)
        self.assertContains(
            response,
            "<h1>Server Error (500)</h1><p>Sorry, there’s a problem with the service.</p>",
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
        )
