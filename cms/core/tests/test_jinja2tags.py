# Tests to check the filter for the custom date format in the CMS

from datetime import datetime

from django.test import SimpleTestCase

from cms.core.templatetags.util_tags import custom_date_format


class CustomDateFormatTests(SimpleTestCase):
    def setUp(self):
        self.am = datetime(2013, 3, 1, 9, 30)
        self.pm = datetime(1990, 3, 1, 18, 45)

    # tests datetime format for am
    def test_datetime_format_am(self):
        result = custom_date_format(self.am, "DATETIME_FORMAT")
        self.assertEqual(result, "1 March 2013 9:30am")

    # tests datetime format for pm
    def test_datetime_format_pm(self):
        result = custom_date_format(self.pm, "DATETIME_FORMAT")
        self.assertEqual(result, "1 March 1990 6:45pm")

    # tests format string 'a' for am
    def test_format_string_a_am(self):
        result = custom_date_format(self.am, "a")
        self.assertEqual(result, "am")

    # tests format string 'a' for pm
    def test_format_string_a_pm(self):
        result = custom_date_format(self.pm, "a")
        self.assertEqual(result, "pm")

    # tests for empty input
    def test_value_none(self):
        self.assertEqual(custom_date_format(None, "a"), "")
