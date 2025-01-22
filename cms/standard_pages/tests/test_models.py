from django.test import TestCase
from wagtail.test.utils import WagtailTestUtils

from cms.core.tests.factories import (
    FeaturedItemBlockFactory,
)
from cms.standard_pages.tests.factories import IndexPageFactory


class IndexPageTestCase(WagtailTestUtils, TestCase):
    """Test IndexPage model properties and methods."""

    def setUp(self):
        self.page = IndexPageFactory(
            title="Test Index Page",
            description="This is an example",
            content="This is the main content",
            featured_items=None,
            related_links=None,
        )

        self.page_url = self.page.url

    def test_custom_featured_items_are_displayed_correctly(self):
        """Test that the custom featured items are displayed on the page."""
        featured_items_dict = [
            {
                "featured_item",
                {
                    "title": "Title of the custom featured item",
                    "description": "Description of the custom featured item",
                    "external_url": "external-url.com"
            }
            }
        ]

        # featured_items_dict_explicit_keys = [
        # {
        #     "type": "featured_item",
        #     "value": {
        #             "title": "Title of the custom featured item",
        #             "description": "Description of the custom featured item",
        #             "external_url": "external-url.com"
        #     }
        # }
        # ]

        # featured_items_subfactory = [
        #     {
        #         "featured_item",
        #         FeaturedItemBlockFactory(
        #             title="Title of the custom featured item",
        #             description="Description of the custom featured item",
        #             external_url="external-url.com",
        #         ),
        #     }
        # ]

        # featured_items_subfactory_explicit_keys = [
        #     {
        #         "type": "featured_item",
        #         "value": FeaturedItemBlockFactory(
        #             title="Title of the custom featured item",
        #             description="Description of the custom featured item",
        #             external_url="external-url.com",
        #         ),
        #     }
        # ]

        self.page.featured_items = featured_items_dict

        response = self.client.get(self.page_url)
        self.assertContains(response, "ons-document-list")
        self.assertEqual(response.status_code, 200)
