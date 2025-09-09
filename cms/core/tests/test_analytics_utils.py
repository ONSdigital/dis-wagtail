from datetime import date, datetime

from django.test import SimpleTestCase

from cms.core.analytics_utils import add_table_of_contents_gtm_attributes, bool_to_yes_no, format_date_for_gtm


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
