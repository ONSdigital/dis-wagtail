from django.test import TestCase, override_settings

from cms.home.models import HomePage


class HomePageTestCase(TestCase):
    def setUp(self):
        self.home_page = HomePage.objects.get()

        self.url = self.home_page.get_url()

    def test_loads(self):
        """Test the homepage loads."""
        with self.assertNumQueries(13):
            response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)

    @override_settings(IS_EXTERNAL_ENV=True)
    def test_external_env(self):
        """Test the homepage loads in external environment."""
        with self.assertNumQueries(10):
            response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
