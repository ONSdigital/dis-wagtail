from django.contrib.contenttypes.models import ContentType
from django.test import TestCase, override_settings

from cms.home.models import HomePage


class HomePageTestCase(TestCase):
    def setUp(self):
        self.home_page = HomePage.objects.get()

        self.url = self.home_page.get_url()

        # Populate contenttype cache to avoid extra query
        ContentType.objects.get_for_model(HomePage)

    def test_loads(self):
        """Test the homepage loads."""
        with self.assertNumQueries(13):
            response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)

    @override_settings(IS_EXTERNAL_ENV=True)
    def test_external_env(self):
        """Test the homepage loads in external environment."""
        with self.assertNumQueries(9):
            response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
