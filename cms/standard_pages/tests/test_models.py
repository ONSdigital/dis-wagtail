from datetime import datetime

from django.http import Http404
from django.test import RequestFactory, TestCase, override_settings
from wagtail.test.utils import WagtailTestUtils

from cms.articles.tests.factories import StatisticalArticlePageFactory
from cms.core.enums import RelatedContentType
from cms.datavis.tests.factories import make_table_block_value
from cms.standard_pages.tests.factories import IndexPageFactory, InformationPageFactory


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


class InformationPageCSVDownloadTestCase(WagtailTestUtils, TestCase):
    """Test InformationPage CSV download functionality via CoreCSVDownloadMixin."""

    def setUp(self):
        self.page = InformationPageFactory(title="Information Page")
        self.factory = RequestFactory()

    def test_get_table_returns_table_block_by_id(self):
        """Test get_table returns the correct table from content."""
        self.page.content = [
            {
                "type": "table",
                "value": make_table_block_value(title="Test Table 1"),
                "id": "test-table-id-1",
            },
            {
                "type": "table",
                "value": make_table_block_value(title="Test Table 2"),
                "id": "test-table-id-2",
            },
        ]

        table = self.page.get_table("test-table-id-1")
        self.assertEqual(table["title"], "Test Table 1")

        table = self.page.get_table("test-table-id-2")
        self.assertEqual(table["title"], "Test Table 2")

    def test_get_table_returns_empty_dict_when_not_found(self):
        """Test get_table returns empty dict when table_id is not found."""
        self.page.content = []

        table = self.page.get_table("unknown-table-id")
        self.assertEqual(table, {})

    def test_get_table_data_for_csv_extracts_headers_and_rows(self):
        """Test get_table_data_for_csv flattens table data correctly."""
        self.page.content = [
            {
                "type": "table",
                "value": make_table_block_value(
                    title="CSV Test Table",
                    headers=[["Year", "Value"]],
                    rows=[["2020", "100"], ["2021", "150"]],
                ),
                "id": "csv-table-id",
            }
        ]

        csv_data = self.page.get_table_data_for_csv("csv-table-id")

        self.assertEqual(csv_data[0], ["Year", "Value"])
        self.assertEqual(csv_data[1], ["2020", "100"])
        self.assertEqual(csv_data[2], ["2021", "150"])
        self.assertEqual(len(csv_data), 3)

    def test_get_table_data_for_csv_raises_for_missing_table(self):
        """Test get_table_data_for_csv raises ValueError for missing table."""
        self.page.content = []

        with self.assertRaises(ValueError) as context:
            self.page.get_table_data_for_csv("nonexistent-table-id")

        self.assertIn("not found", str(context.exception))

    def test_download_table_returns_csv(self):
        """Test download_table returns a CSV response."""
        self.page.content = [
            {
                "type": "table",
                "value": make_table_block_value(
                    title="Download Test Table",
                    headers=[["Col1", "Col2"]],
                    rows=[["A", "B"]],
                ),
                "id": "download-table-id",
            }
        ]
        self.page.save_revision().publish()

        request = self.factory.get("/fake-path/")
        response = self.page.download_table(request, "download-table-id")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/csv")
        self.assertIn("attachment", response["Content-Disposition"])
        self.assertIn("download-test-table.csv", response["Content-Disposition"].lower())

    def test_download_table_raises_404_for_missing_table(self):
        """Test download_table raises Http404 when table not found."""
        self.page.content = []
        request = self.factory.get("/fake-path/")

        with self.assertRaises(Http404):
            self.page.download_table(request, "nonexistent-table-id")
