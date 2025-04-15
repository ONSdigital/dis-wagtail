from datetime import datetime

from django.test import SimpleTestCase

from cms.core.templatetags.util_tags import ons_date_format_filter


class CustomDateFormatTests(SimpleTestCase):
    def setUp(self):
        self.am = datetime(2013, 3, 1, 9, 30)
        self.pm = datetime(1990, 3, 1, 18, 45)

    def test_datetime_format_am(self):
        result = ons_date_format_filter(self.am, "DATETIME_FORMAT")
        self.assertEqual(result, "1 March 2013 9:30am")

    def test_datetime_format_pm(self):
        result = ons_date_format_filter(self.pm, "DATETIME_FORMAT")
        self.assertEqual(result, "1 March 1990 6:45pm")

    def test_format_string_a_am(self):
        result = ons_date_format_filter(self.am, "a")
        self.assertEqual(result, "am")

    def test_format_string_a_pm(self):
        result = ons_date_format_filter(self.pm, "a")
        self.assertEqual(result, "pm")

    def test_value_none(self):
        self.assertEqual(ons_date_format_filter(None, "a"), "")
