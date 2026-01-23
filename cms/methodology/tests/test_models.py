from datetime import datetime

from django.conf import settings
from django.core.exceptions import ValidationError
from django.http import Http404
from django.test import RequestFactory, TestCase, override_settings
from django.utils.formats import date_format
from wagtail.test.utils import WagtailTestUtils

from cms.core.tests.factories import ContactDetailsFactory
from cms.datavis.tests.factories import TableDataFactory, make_table_block_value
from cms.methodology.tests.factories import MethodologyPageFactory, MethodologyRelatedPageFactory


class MethodologyPageTestCase(WagtailTestUtils, TestCase):
    """Test MethodologyPage model properties and methods."""

    def setUp(self):
        self.page = MethodologyPageFactory(
            parent__title="Topic Page",
            title="Methodology Page",
            publication_date=datetime(2024, 8, 15),
            show_cite_this_page=False,
            contact_details=None,
        )
        self.page_url = self.page.url

    def test_table_of_contents_with_content(self):
        """Test table_of_contents with content blocks."""
        self.page.content = [
            {"type": "section", "value": {"title": "Test Section", "content": [{"type": "rich_text", "value": "text"}]}}
        ]

        toc = self.page.table_of_contents
        self.assertEqual(len(toc), 1)
        toc_item = toc[0]
        self.assertEqual(toc_item["url"], "#test-section")
        self.assertEqual(toc_item["text"], "Test Section")

    def test_table_of_contents_with_contact_details(self):
        """Test table_of_contents includes contact details when present."""
        self.page.contact_details = ContactDetailsFactory()
        toc = self.page.table_of_contents
        self.assertEqual(len(toc), 1)
        toc_item = toc[0]
        self.assertEqual(toc_item["url"], "#contact-details")
        self.assertEqual(toc_item["text"], "Contact details")

    def test_table_of_contents_without_related_publications(self):
        MethodologyRelatedPageFactory(parent=self.page)
        toc = self.page.table_of_contents
        self.assertEqual(len(toc), 1)
        toc_item = toc[0]
        self.assertEqual(toc_item["url"], "#related-publications")
        self.assertEqual(toc_item["text"], "Related publications")

    def test_cite_this_page_is_not_shown_when_unticked(self):
        """Test for the cite this page block not present in the template."""
        latest_date_formatted = date_format(self.page.last_revised_date, settings.DATE_FORMAT)

        cite_fragment = (
            f"Office for National Statistics (ONS), last revised {latest_date_formatted}, "
            f'ONS website, methodology, <a href="{self.page.full_url}">{self.page.title}</a>'
        )
        response = self.client.get(self.page_url)
        self.assertNotContains(response, cite_fragment)

    def test_cite_this_page_is_shown_when_ticked(self):
        """Test for the cite this page block."""
        self.page.show_cite_this_page = True
        self.page.save(update_fields=["show_cite_this_page"])
        latest_date_formatted = date_format(self.page.last_revised_date, settings.DATE_FORMAT)

        cite_fragment = (
            f"Office for National Statistics (ONS), last revised {latest_date_formatted}, "
            f'ONS website, methodology, <a href="{self.page.full_url}">{self.page.title}</a>'
        )
        response = self.client.get(self.page_url)
        self.assertContains(response, cite_fragment)

    def test_last_revised_date_must_be_after_publication_date(self):
        """Tests the model validates last revised date is after the publication date."""
        self.page.last_revised_date = self.page.publication_date

        with self.assertRaises(ValidationError) as info:
            self.page.clean()

        self.assertEqual(info.exception.messages, ["The last revised date must be after the published date."])

    def test_related_publications(self):
        related = [
            MethodologyRelatedPageFactory(parent=self.page, page__title="Article Series 1"),
            MethodologyRelatedPageFactory(parent=self.page, page__title="Another Article Series 2"),
            MethodologyRelatedPageFactory(parent=self.page, page__title="Unpublished Article Series", page__live=False),
        ]

        self.assertListEqual(
            list(self.page.related_publications.values_list("pk", flat=True)), [related[0].page_id, related[1].page_id]
        )

    def test_get_formatted_related_publications_list(self):
        related = MethodologyRelatedPageFactory(parent=self.page, page__title="The Article Series 1")

        self.assertEqual(
            self.page.get_formatted_related_publications_list(),
            {
                "title": "Related publications",
                "itemsList": [{"title": related.page.display_title, "url": related.page.url}],
            },
        )

    @override_settings(IS_EXTERNAL_ENV=True)
    def test_render_in_external_env(self):
        """Test that the page renders in external environment."""
        response = self.client.get(self.page_url)

        self.assertEqual(response.status_code, 200)


class MethodologyPageCSVDownloadTestCase(WagtailTestUtils, TestCase):
    """Test MethodologyPage CSV download functionality via CSVDownloadMixin."""

    def setUp(self):
        self.page = MethodologyPageFactory(
            parent__title="Topic Page",
            title="Methodology Page",
            publication_date=datetime(2024, 8, 15),
        )
        self.factory = RequestFactory()

    def test_get_table_returns_table_block_by_id(self):
        """Test get_table returns the correct table from content sections."""
        self.page.content = [
            {
                "type": "section",
                "value": {
                    "title": "Table Section",
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
        self.page.content = [
            {
                "type": "section",
                "value": {
                    "title": "Empty Section",
                    "content": [],
                },
            }
        ]

        table = self.page.get_table("unknown-table-id")
        self.assertEqual(table, {})

    def test_get_chart_returns_chart_block_by_id(self):
        """Test get_chart returns the correct chart from content sections."""
        self.page.content = [
            {
                "type": "section",
                "value": {
                    "title": "Chart Section",
                    "content": [
                        {
                            "type": "line_chart",
                            "value": {
                                "title": "Test Chart",
                                "table": TableDataFactory(),
                            },
                            "id": "test-chart-id",
                        },
                    ],
                },
            }
        ]

        chart = self.page.get_chart("test-chart-id")
        self.assertEqual(chart["title"], "Test Chart")

    def test_get_chart_returns_empty_dict_when_not_found(self):
        """Test get_chart returns empty dict when chart_id is not found."""
        self.page.content = [
            {
                "type": "section",
                "value": {
                    "title": "Empty Section",
                    "content": [],
                },
            }
        ]

        chart = self.page.get_chart("unknown-chart-id")
        self.assertEqual(chart, {})

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

    def test_download_chart_returns_csv(self):
        """Test download_chart returns a CSV response."""
        self.page.content = [
            {
                "type": "section",
                "value": {
                    "title": "Download Chart Section",
                    "content": [
                        {
                            "type": "line_chart",
                            "value": {
                                "title": "Download Test Chart",
                                "table": TableDataFactory(
                                    table_data=[
                                        ["Category", "Value"],
                                        ["A", "10"],
                                        ["B", "20"],
                                    ]
                                ),
                            },
                            "id": "download-chart-id",
                        }
                    ],
                },
            }
        ]
        self.page.save_revision().publish()

        request = self.factory.get("/fake-path/")
        response = self.page.download_chart(request, "download-chart-id")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/csv")
        self.assertIn("attachment", response["Content-Disposition"])
        self.assertIn("download-test-chart.csv", response["Content-Disposition"].lower())

    def test_download_chart_raises_404_for_missing_chart(self):
        """Test download_chart raises Http404 when chart not found."""
        self.page.content = []
        request = self.factory.get("/fake-path/")

        with self.assertRaises(Http404):
            self.page.download_chart(request, "nonexistent-chart-id")
