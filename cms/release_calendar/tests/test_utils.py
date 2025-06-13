from datetime import date

from django.test import TestCase

from cms.release_calendar.utils import parse_month_year


class ParseMonthYearTestCase(TestCase):
    def test_parse_month_year(self):
        cases = [
            ("January 2023", "en", date(2023, 1, 1)),
            ("February 2023", "en", date(2023, 2, 1)),
            ("Mar 2023", "en", None),
            ("May 2023", "en", date(2023, 5, 1)),
            ("January 2023", "cy", None),
            ("Ionawr 2023", "cy", date(2023, 1, 1)),
            ("Chwefror 2023", "cy", date(2023, 2, 1)),
            ("Mawrth 2023", "cy", date(2023, 3, 1)),
            ("April 2023", "ja", None),
            ("April 23", "en", None),
            ("April Problematic", "en", None),
            ("2023 April", "en", None),
            ("", "", None),
            ("", "en", None),
        ]
        for text, locale, parse_result in cases:
            with self.subTest(text=text, locale=locale, parse_result=parse_result):
                self.assertEqual(parse_month_year(text, locale), parse_result)
