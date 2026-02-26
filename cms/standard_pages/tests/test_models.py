from django.http import Http404
from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse
from wagtail.test.utils import WagtailTestUtils

from cms.core.permission_testers import BasePagePermissionTester
from cms.datavis.tests.factories import make_table_block_value
from cms.home.models import HomePage
from cms.standard_pages.tests.factories import IndexPageFactory, InformationPageFactory
from cms.users.tests.factories import UserFactory


class IndexPageTestCase(WagtailTestUtils, TestCase):
    """Test IndexPage model properties and methods."""

    @classmethod
    def setUpTestData(cls):
        cls.index_page = IndexPageFactory(
            title="Test Index Page",
            summary="This is an example",
        )

        cls.page_url = cls.index_page.url

        cls.request_factory = RequestFactory()

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

    def test_get_cached_paths(self):
        self.page.content = [
            {
                "type": "section",
                "value": {
                    "title": "Content",
                    "content": [
                        {
                            "id": "test-table-id",
                            "type": "table",
                            "value": make_table_block_value(
                                title="Test Table 1",
                                caption="Table caption 1",
                                source="Test Source",
                                headers=[["Header 1"]],
                                rows=[["Row 1 Col 1"]],
                            ),
                        },
                    ],
                },
            }
        ]

        self.assertEqual(self.page.get_cached_paths(), ["/", "/download-table/test-table-id"])


class StandardPagesAddViewTests(WagtailTestUtils, TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.permission_denied_message = "Sorry, you do not have permission to access this area."
        cls.index_page = IndexPageFactory()

    def setUp(self):
        self.login()

    def test_index_page_cannot_have_index_page_child(self):
        """Home -> Index Page -> Index Page should be forbidden."""
        response = self.client.get(
            reverse("wagtailadmin_pages:add", args=("standard_pages", "indexpage", self.index_page.pk)),
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.permission_denied_message)

    def test_information_page_cannot_have_information_page_child(self):
        """Home -> Index Page -> Information Page -> Information Page should be forbidden."""
        information_page = InformationPageFactory(parent=self.index_page)

        response = self.client.get(
            reverse("wagtailadmin_pages:add", args=("standard_pages", "informationpage", information_page.pk)),
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.permission_denied_message)

    def test_information_page_cannot_be_added_under_home(self):
        """Home -> Information Page should be forbidden."""
        home_page = HomePage.objects.first()

        response = self.client.get(
            reverse("wagtailadmin_pages:add", args=("standard_pages", "informationpage", home_page.pk)),
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.permission_denied_message)

    def test_index_page_can_be_added_under_home(self):
        """Home -> Index Page should be allowed."""
        home_page = HomePage.objects.first()

        response = self.client.get(
            reverse("wagtailadmin_pages:add", args=("standard_pages", "indexpage", home_page.pk)),
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, self.permission_denied_message)

    def test_information_page_can_be_added_under_index_page(self):
        """Home -> Index Page -> Information Page should be allowed."""
        response = self.client.get(
            reverse("wagtailadmin_pages:add", args=("standard_pages", "informationpage", self.index_page.pk)),
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, self.permission_denied_message)


class InformationPageCSVDownloadTestCase(WagtailTestUtils, TestCase):
    """Test InformationPage CSV download functionality via CoreCSVDownloadMixin."""

    def setUp(self):
        self.page = InformationPageFactory(title="Information Page")
        self.factory = RequestFactory()

    def test_get_table_returns_table_block_by_id(self):
        """Test get_table returns the correct table from content."""
        self.page.content = [
            {
                "type": "section",
                "value": {
                    "title": "Test Section",
                    "content": [
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
                    ],
                },
            }
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
                "type": "section",
                "value": {
                    "title": "CSV Table Section",
                    "content": [
                        {
                            "type": "table",
                            "value": make_table_block_value(
                                title="CSV Test Table",
                                headers=[["Year", "Value"]],
                                rows=[["2020", "100"], ["2021", "150"]],
                            ),
                            "id": "csv-table-id",
                        }
                    ],
                },
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
                "type": "section",
                "value": {
                    "title": "Download Table Section",
                    "content": [
                        {
                            "type": "table",
                            "value": make_table_block_value(
                                title="Download Test Table",
                                headers=[["Col1", "Col2"]],
                                rows=[["A", "B"]],
                            ),
                            "id": "download-table-id",
                        }
                    ],
                },
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

    def test_get_table_data_for_csv_raises_for_empty_data(self):
        """Test get_table_data_for_csv raises ValueError when table has no data."""
        self.page.content = [
            {
                "type": "section",
                "value": {
                    "title": "Empty Table Section",
                    "content": [
                        {
                            "type": "table",
                            "value": {
                                "title": "Empty Data Table",
                                "data": {
                                    "headers": [],
                                    "rows": [],
                                },
                            },
                            "id": "empty-data-table-id",
                        }
                    ],
                },
            }
        ]

        with self.assertRaises(ValueError) as context:
            self.page.get_table_data_for_csv("empty-data-table-id")

        self.assertIn("no data", str(context.exception))

    def test_download_table_uses_caption_as_fallback_title(self):
        """Test download_table uses caption for filename when title is empty."""
        self.page.content = [
            {
                "type": "section",
                "value": {
                    "title": "Caption Table Section",
                    "content": [
                        {
                            "type": "table",
                            "value": make_table_block_value(
                                title="",
                                caption="Caption Table",
                                headers=[["A"]],
                                rows=[["1"]],
                            ),
                            "id": "caption-table-id",
                        }
                    ],
                },
            }
        ]
        self.page.save_revision().publish()

        request = self.factory.get("/fake-path/")
        response = self.page.download_table(request, "caption-table-id")

        self.assertEqual(response.status_code, 200)
        self.assertIn("caption-table.csv", response["Content-Disposition"].lower())

    def test_download_table_uses_default_title_when_no_title_or_caption(self):
        """Test download_table uses 'table' as filename when no title or caption."""
        self.page.content = [
            {
                "type": "section",
                "value": {
                    "title": "No Title Section",
                    "content": [
                        {
                            "type": "table",
                            "value": {
                                "title": "",
                                "data": {
                                    "headers": [[{"value": "H", "type": "th"}]],
                                    "rows": [[{"value": "V", "type": "td"}]],
                                },
                            },
                            "id": "no-title-table-id",
                        }
                    ],
                },
            }
        ]
        self.page.save_revision().publish()

        request = self.factory.get("/fake-path/")
        response = self.page.download_table(request, "no-title-table-id")

        self.assertEqual(response.status_code, 200)
        # Should default to "table.csv"
        self.assertIn("table.csv", response["Content-Disposition"].lower())

    def test_get_table_ignores_non_table_blocks(self):
        """Test get_table only matches table block types."""
        self.page.content = [
            {
                "type": "section",
                "value": {
                    "title": "Mixed Content Section",
                    "content": [
                        {
                            "type": "rich_text",
                            "value": "Some text",
                            "id": "rich-text-id",
                        },
                        {
                            "type": "table",
                            "value": make_table_block_value(title="Actual Table"),
                            "id": "table-id",
                        },
                    ],
                },
            }
        ]

        # Should not find rich_text block even with matching ID pattern
        self.assertEqual(self.page.get_table("rich-text-id"), {})
        # Should find table block
        self.assertEqual(self.page.get_table("table-id")["title"], "Actual Table")

    def test_get_table_requires_block_id(self):
        """Test get_table returns empty dict for blocks without an id."""
        self.page.content = [
            {
                "type": "section",
                "value": {
                    "title": "No ID Section",
                    "content": [
                        {
                            "type": "table",
                            "value": make_table_block_value(title="Table Without ID"),
                            # No "id" key
                        }
                    ],
                },
            }
        ]

        # Should not find anything - blocks need IDs to be retrieved
        self.assertEqual(self.page.get_table("any-id"), {})

    def test_download_table_endpoint_via_url(self):
        """Test download_table endpoint is accessible via URL."""
        self.page.content = [
            {
                "type": "section",
                "value": {
                    "title": "URL Test Section",
                    "content": [
                        {
                            "type": "table",
                            "value": make_table_block_value(
                                title="URL Test Table",
                                headers=[["X"]],
                                rows=[["Y"]],
                            ),
                            "id": "url-test-table-id",
                        }
                    ],
                },
            }
        ]
        self.page.save_revision().publish()

        response = self.client.get(f"{self.page.url}/download-table/url-test-table-id")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/csv")

    def test_download_table_endpoint_returns_404_for_nonexistent_table(self):
        """Test download_table endpoint returns 404 when table not found."""
        self.page.content = []
        self.page.save_revision().publish()

        response = self.client.get(f"{self.page.url}/download-table/nonexistent-id")

        self.assertEqual(response.status_code, 404)
