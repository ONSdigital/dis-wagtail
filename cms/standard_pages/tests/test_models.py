from django.test import TestCase, override_settings
from wagtail.test.utils import WagtailTestUtils

from cms.standard_pages.tests.factories import IndexPageFactory, InformationPageFactory


class IndexPageTestCase(WagtailTestUtils, TestCase):
    """Test IndexPage model properties and methods."""

    @classmethod
    def setUpTestData(cls):
        cls.index_page = IndexPageFactory(
            title="Test Index Page",
            summary="This is an example",
        )

        cls.page_url = cls.index_page.url

    def test_no_featured_items_displayed_when_no_children_and_no_custom_featured_items_selected(self):
        """Test that the Featured Items block isn't displayed when the Index Page has no child pages
        and no custom Featured Items are specified.
        """
        response = self.client.get(self.page_url)

        self.assertEqual(response.status_code, 200)

        self.assertNotContains(response, "ons-document-list")

    def test_children_displayed_as_featured_items_when_no_custom_featured_items_selected(self):
        """Test that the children pages of the Index Page are displayed
        when no custom Featured Items are specified.
        """
        child_page = InformationPageFactory(parent=self.index_page)

        response = self.client.get(self.page_url)

        self.assertEqual(response.status_code, 200)

        self.assertContains(response, child_page.title)
        self.assertContains(response, child_page.url)
        self.assertContains(response, child_page.summary)

    def test_children_displayed_as_featured_items_with_listing_info_when_no_custom_featured_items_selected(self):
        """Test that the children pages of the Index page are displayed
        when no custom Featured Items are specified
        and that the child pages is displayed with its listing title and listing summary.
        """
        child_page_listing_info = InformationPageFactory(
            title="Title of the child page",
            summary="Summary of the child page",
            parent=self.index_page,
            listing_title="Listing title of the child page",
            listing_summary="Listing summary of the child page",
        )

        response = self.client.get(self.page_url)

        self.assertEqual(response.status_code, 200)

        self.assertContains(response, child_page_listing_info.listing_title)
        self.assertContains(response, child_page_listing_info.url)
        self.assertContains(response, child_page_listing_info.listing_summary)

        self.assertNotContains(response, child_page_listing_info.title)
        self.assertNotContains(response, child_page_listing_info.summary)

    @override_settings(IS_EXTERNAL_ENV=True)
    def test_load_in_external_env(self):
        """Test the page loads in external env."""
        response = self.client.get(self.page_url)
        self.assertEqual(response.status_code, 200)


class InformationPageTestCase(WagtailTestUtils, TestCase):
    """Test InformationPage model properties and methods."""

    @classmethod
    def setUpTestData(cls):
        cls.page = InformationPageFactory(title="Test Information Page")

        cls.page_url = cls.page.url

    def test_page_loads(self):
        """Test that the Information Page loads correctly."""
        response = self.client.get(self.page_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.page.title)
        self.assertContains(response, self.page.content)
