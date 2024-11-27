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
        with self.assertNoDefaultQueries(), self.assertNumQueries(4, using="read_replica"):
            self.client.get(self.url)
