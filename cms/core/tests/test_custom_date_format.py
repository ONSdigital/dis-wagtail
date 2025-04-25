from datetime import datetime

from django.test import SimpleTestCase

from cms.core.custom_date_format import ons_date_format


class CustomDateFormatTests(SimpleTestCase):
    """Unit tests for the helpers in custom_date_format.py."""

    def test_meridiem_boundary(self):
        """00:00-11:59  →  'am'
        12:00-23:59 →  'pm'.
        """
        hours_expected = {
            0: "am",  # midnight
            11: "am",
            12: "pm",  # noon
            23: "pm",
        }

        for hour, expected in hours_expected.items():
            dt = datetime(2025, 11, 1, hour, 30)  # 1 Nov 2025 HH:30
            rendered = ons_date_format(dt, "DATETIME_FORMAT")
            self.assertTrue(
                rendered.endswith(expected),
                msg=f"{hour:02d}:30 should end with '{expected}', got {rendered!r}",
            )
