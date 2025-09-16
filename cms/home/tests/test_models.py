from django.test import TestCase, override_settings
from wagtail.coreutils import get_dummy_request

from cms.home.models import HomePage


class HomePageTestCase(TestCase):
    def setUp(self):
        self.home_page = HomePage.objects.first()

        self.url = self.home_page.get_url()

    def test_loads(self):
        """Test the homepage loads."""
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)

    @override_settings(IS_EXTERNAL_ENV=True)
    def test_external_env(self):
        """Test the homepage loads in external environment."""
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)

    def test_localised_root(self):
        """Test the homepage loads for a localised root URL."""
        response = self.client.get("/cy")

        self.assertEqual(response.status_code, 200)

    @override_settings(USE_I18N_ROOT_NO_TRAILING_SLASH=False)
    def test_localised_root_no_trailing_slash_disabled(self):
        """Test the localised root URL returns 404 if the setting is disabled."""
        response = self.client.get("/cy")

        self.assertEqual(response.status_code, 404)

    def test_get_analytics_values(self):
        analytics_values = self.home_page.get_analytics_values(get_dummy_request())
        self.assertEqual(analytics_values["pageTitle"], self.home_page.title)
        self.assertEqual(analytics_values["contentType"], self.home_page.analytics_content_type)
