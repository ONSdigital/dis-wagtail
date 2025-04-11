from datetime import datetime

from django.test import SimpleTestCase

from cms.core.custom_dateformat import ons_date_format


class NewDateFormatTests(SimpleTestCase):
    def test_am(self):
        am = datetime(2025, 3, 1, 7, 30)
        result = ons_date_format(am, "a")
        self.assertEqual(result, "am")

    def test_pm(self):
        pm = datetime(2025, 3, 1, 18, 30)
        result = ons_date_format(pm, "a")
        self.assertEqual(result, "pm")
