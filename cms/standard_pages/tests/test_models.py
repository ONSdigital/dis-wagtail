from datetime import datetime

from django.test import TestCase, override_settings
from wagtail.test.utils import WagtailTestUtils

from cms.articles.tests.factories import StatisticalArticlePageFactory
from cms.core.enums import RelatedContentType
from cms.core.permission_testers import BasePagePermissionTester
from cms.standard_pages.tests.factories import IndexPageFactory, InformationPageFactory
from cms.users.tests.factories import UserFactory


class IndexPageTestCase(WagtailTestUtils, TestCase):
    """Test IndexPage model properties and methods."""

    @classmethod
    def setUpTestData(cls):
        cls.index_page = IndexPageFactory(
            title="Test Index Page",
            summary="This is an example",
            content="This is the main content",
            featured_items=None,
            related_links=None,
        )

        cls.page_url = cls.index_page.url

    def test_permission_tester_inherits_from_basepagepermissiontester(self):
        self.assertIsInstance(self.index_page.permissions_for_user(UserFactory()), BasePagePermissionTester)

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

    def test_custom_featured_item_external_page_is_displayed_correctly(self):
        """Test that the custom featured items are displayed on the page."""
        featured_item_external_page = {
            "type": "featured_item",
            "value": {
                "title": "Title of the custom featured item",
                "description": "Description of the custom featured item",
                "external_url": "external-url.com",
                "release_date": "2025-01-01",
            },
        }

        self.index_page.featured_items = [featured_item_external_page]
        self.index_page.save_revision().publish()

        response = self.client.get(self.page_url)

        self.assertEqual(response.status_code, 200)

        self.assertContains(response, featured_item_external_page["value"]["title"])
        self.assertContains(response, featured_item_external_page["value"]["external_url"])
        self.assertContains(response, featured_item_external_page["value"]["description"])

    def test_custom_featured_item_internal_page_is_displayed_correctly(self):
        """Test that the custom featured item is displayed on the page
        and that the child page isn't displayed on the page.
        """
        child_page = InformationPageFactory(parent=self.index_page, title="Child page")

        internal_page = StatisticalArticlePageFactory(release_date=datetime(2025, 1, 1))

        featured_item_internal_page = {
            "type": "featured_item",
            "value": {
                "page": internal_page.id,
                "description": "Description of the custom featured item",
            },
        }

        self.index_page.featured_items = [featured_item_internal_page]
        self.index_page.save_revision().publish()

        response = self.client.get(self.page_url)
        self.assertEqual(response.status_code, 200)

        self.assertContains(response, internal_page.display_title)
        self.assertContains(response, internal_page.url)
        self.assertContains(response, featured_item_internal_page["value"]["description"])
        self.assertContains(response, "Released")
        self.assertContains(response, "1 January 2025")
        self.assertContains(response, "Article")

        self.assertNotContains(response, child_page.title)
        self.assertNotContains(response, child_page.url)
        self.assertNotContains(response, child_page.summary)

    def test_get_formatted_related_links_list_works_for_internal_pages(self):
        """Test that the links to internal pages rare returned
        in a format that can be consumed by the Design System list component.
        """
        internal_page = InformationPageFactory(parent=self.index_page)

        self.index_page.related_links = [{"type": "related_link", "value": {"page": internal_page.id}}]

        formatted_related_links = self.index_page.get_formatted_related_links_list()

        self.assertEqual(formatted_related_links, [{"title": internal_page.title, "url": internal_page.url}])

    def test_get_formatted_related_links_list_works_for_external_pages(self):
        """Test that the links to external pages are returned
        in a format that can be consumed by the Design System list component.
        """
        self.index_page.related_links = [
            {"type": "related_link", "value": {"title": "An external page", "external_url": "external-url.com"}}
        ]

        formatted_related_links = self.index_page.get_formatted_related_links_list()

        self.assertEqual(formatted_related_links, [{"title": "An external page", "url": "external-url.com"}])

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

    def test_permission_tester_inherits_from_basepagepermissiontester(self):
        self.assertIsInstance(self.page.permissions_for_user(UserFactory()), BasePagePermissionTester)

    def test_page_loads(self):
        """Test that the Information Page loads correctly."""
        response = self.client.get(self.page_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.page.title)
        self.assertContains(response, self.page.content)

    def test_related_links(self):
        another_information_page = InformationPageFactory(
            title="Another Information Page",
            parent=self.page.get_parent(),
        )
        self.page.content = [
            {
                "type": "related_links",
                "value": [
                    {
                        "title": "An external page",
                        "external_url": "external-url.com",
                        "release_date": "2025-05-21",
                        "content_type": RelatedContentType.ARTICLE,
                    },
                    {
                        "page": another_information_page.pk,
                        "release_date": "2025-01-02",
                        "content_type": RelatedContentType.TIME_SERIES,
                    },
                ],
            }
        ]

        self.page.save_revision().publish()

        response = self.client.get(self.page_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Related links")  # Should have a heading added
        self.assertContains(response, "An external page")
        self.assertContains(response, "external-url.com")
        self.assertContains(response, "Article")
        self.assertContains(response, "21 May 2025")
        self.assertContains(response, another_information_page.title)
        self.assertContains(response, "2 January 2025")
        self.assertContains(response, "Time series")
