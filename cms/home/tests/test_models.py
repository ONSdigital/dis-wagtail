from django.test import TestCase, override_settings

from cms.core.tests import TransactionTestCase
from cms.home.models import HomePage


class HomePageTestCase(TestCase):
    def setUp(self):
        self.home_page = HomePage.objects.get()

        self.url = self.home_page.get_url()

    def test_loads(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)

    def test_queries(self):
        with self.assertNumQueries(12):
            response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    @override_settings(IS_EXTERNAL_ENV=True)
    def test_external_env(self):
        with self.assertNumQueries(9):
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
