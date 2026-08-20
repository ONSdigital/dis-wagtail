from datetime import date, datetime

from django.test import SimpleTestCase

from cms.core.analytics_utils import (
    add_table_of_contents_gtm_attributes,
    bool_to_yes_no,
    format_date_for_gtm,
    get_gtm_attributes_file_download,
)


class AnalyticsUtilsTestCase(SimpleTestCase):
    def test_format_date_for_gtm(self):
        d = date(2023, 10, 1)
        self.assertEqual(format_date_for_gtm(d), "20231001")

    def test_format_date_for_gtm_with_datetime(self):
        dt = datetime(2023, 10, 1, 1, 2, 3)
        self.assertEqual(format_date_for_gtm(dt), "20231001")

    def test_bool_to_yes_no(self):
        self.assertEqual(bool_to_yes_no(True), "yes")
        self.assertEqual(bool_to_yes_no(False), "no")

    def test_add_table_of_contents_gtm_attributes(self):
        items = [
            {"text": "Section 1", "url": "#section-1"},
            {"text": "Section 2", "url": "#section-2"},
            {"text": "Section 3", "url": "#section-3"},
        ]
        add_table_of_contents_gtm_attributes(items)

        for item in items:
            self.assertIn("attributes", item)
            self.assertEqual(item["attributes"]["data-ga-section-title"], item["text"])
            self.assertEqual(item["attributes"]["data-ga-event"], "navigation-onpage")
            self.assertEqual(item["attributes"]["data-ga-navigation-type"], "table-of-contents")

    def test_get_gtm_attributes_file_download(self):
        """Checks get_gtm_attributes_file_download returns the correct GTM file download attributes."""
        values = {
            "text": "Download CSV (1KB)",
            "url": "https://testserver:8000/media/files/test-file-name.csv",
            "file_extension": "csv",
            "file_name": "test-file-name.csv",
            "file_size_kb": 1,
        }
        actual = get_gtm_attributes_file_download(
            text=values["text"],
            url=values["url"],
            file_extension=values["file_extension"],
            file_name=values["file_name"],
            file_size_kb=values["file_size_kb"],
        )

        self.assertEqual(actual["data-ga-event"], "file-download")
        self.assertEqual(actual["data-ga-link-text"], values["text"])
        self.assertEqual(actual["data-ga-link-url"], "/media/files/test-file-name.csv")
        self.assertEqual(actual["data-ga-link-domain"], "testserver")
        self.assertEqual(actual["data-ga-file-extension"], values["file_extension"])
        self.assertEqual(actual["data-ga-file-name"], values["file_name"])
        self.assertEqual(actual["data-ga-file-size"], values["file_size_kb"])

    def test_get_gtm_attributes_file_download_when_domain_and_size_are_none(self):
        """Checks domain and file size GTM fields are omitted when the URL is relative and file size is missing."""
        values = {
            "text": "Download CSV (1KB)",
            "url": "/media/files/test-file-name.csv",
            "file_extension": "csv",
            "file_name": "test-file-name.csv",
            "file_size_kb": None,
        }
        actual = get_gtm_attributes_file_download(
            text=values["text"],
            url=values["url"],
            file_extension=values["file_extension"],
            file_name=values["file_name"],
            file_size_kb=values["file_size_kb"],
        )

        self.assertEqual(actual["data-ga-event"], "file-download")
        self.assertEqual(actual["data-ga-link-text"], values["text"])
        self.assertEqual(actual["data-ga-link-url"], values["url"])
        self.assertEqual(actual["data-ga-file-extension"], values["file_extension"])
        self.assertEqual(actual["data-ga-file-name"], values["file_name"])
        self.assertNotIn("data-ga-link-domain", actual)
        self.assertNotIn("data-ga-file-size", actual)
