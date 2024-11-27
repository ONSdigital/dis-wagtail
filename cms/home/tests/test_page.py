from django.test import override_settings

from cms.core.tests import ReadOnlyConnectionTestCase
from cms.home.models import HomePage


class HomePageTestCase(ReadOnlyConnectionTestCase):
    def setUp(self):
        self.home_page = HomePage.objects.get()

        self.url = self.home_page.get_url()

    def test_loads(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)

    def test_queries(self):
        with self.assertTotalNumQueries(12):
            self.client.get(self.url)

        with self.assertTotalNumQueries(8):
            self.client.get(self.url)

    @override_settings(IS_EXTERNAL_ENV=True)
    def test_external_queries(self):
        with self.assertNoDefaultQueries(), self.assertNoWriteQueries(), self.assertTotalNumQueries(9):
            self.client.get(self.url)

        with self.assertNoDefaultQueries(), self.assertNoWriteQueries(), self.assertTotalNumQueries(8):
            self.client.get(self.url)
