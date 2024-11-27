from django.test import TestCase, override_settings

from cms.core.tests import ConnectionHelperMixin, TransactionTestCase
from cms.home.models import HomePage


class HomePageTestCase(ConnectionHelperMixin, TestCase):
    def setUp(self):
        self.home_page = HomePage.objects.get()

        self.url = self.home_page.get_url()

    def test_loads(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)

    def test_queries(self):
        with self.assertTotalNumQueries(12), self.assertNumWriteQueries(1):
            response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    @override_settings(IS_EXTERNAL_ENV=True)
    def test_external_queries(self):
        with self.assertTotalNumQueries(9), self.assertNumWriteQueries(0):
            response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)


class HomePageReadReplicaTestCase(TransactionTestCase):
    def setUp(self):
        self.home_page = HomePage.objects.get()

        self.url = self.home_page.get_url()

    def test_loads(self):
        with self.assertNumQueriesConnection(4, 9):
            response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)

    @override_settings(IS_EXTERNAL_ENV=True)
    def test_loads_external(self):
        with self.assertNumQueriesConnection(0, 8):
            response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
