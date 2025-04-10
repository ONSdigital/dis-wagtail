# Tests to check the custom date format in the CMS

from datetime import datetime

from django.test import SimpleTestCase

from cms.core.custom_dateformat import new_date_format


class NewDateFormatTests(SimpleTestCase):
    # Tests that am input outputs "am"
    def test_am(self):
        am = datetime(2025, 3, 1, 7, 30)
        result = new_date_format(am, "a")
        self.assertEqual(result, "am")

    # Test that an pm input outputs "pm"
    def test_pm(self):
        pm = datetime(2025, 3, 1, 18, 30)
        result = new_date_format(pm, "a")
        self.assertEqual(result, "pm")
