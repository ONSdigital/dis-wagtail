from django.test import TestCase
from wagtail.test.utils import WagtailTestUtils

from cms.standard_pages.tests.factories import IndexPageFactory


class IndexPageTestCase(WagtailTestUtils, TestCase):
    """Test IndexPage model properties and methods."""

    def setUp(self):
        self.page = IndexPageFactory(
            title = "Test Index Page",
            description = "This is an example",
            content = "This is the main content",
            featured_items=None,
            related_links=None
        )

        self.page_url = self.page.full_url


    def test_the_page_is_available(self):

        response = self.client.get(self.page_url)

        print("###############")
        print(f"self.page.url: {self.page.url}")
        print(self.page.__dict__)
        print("###############")

        self.assertEqual(response.status_code, 200)
