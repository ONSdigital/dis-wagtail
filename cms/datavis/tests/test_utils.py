import collections

from django.test import SimpleTestCase

from cms.datavis.blocks.utils import get_approximate_file_size_in_kb
from cms.datavis.utils import numberfy

Case = collections.namedtuple("Case", ["arg", "expected", "description"])


class NumberfyTestCase(SimpleTestCase):
    """Tests of the numberfy function.

    NOTE Any leading or trailing spaces in string arguments are deliberate.
    """

    def test_numberfy(self):
        cases = [
            Case(arg="123", expected=123, description="int string"),
            Case(arg="123.45", expected=123.45, description="float string"),
            Case(arg="foo", expected="foo", description="string"),
            Case(arg="  123 ", expected=123, description="int string with spaces"),
            Case(arg="  123.45 ", expected=123.45, description="float string with spaces"),
            Case(arg="  foo bar ", expected="  foo bar ", description="spaces preserved in strings"),
            Case(arg="-123", expected=-123, description="negative int string"),
            Case(arg=" -123.45 ", expected=-123.45, description="negative float string with spaces"),
            Case(arg="123,", expected="123,", description="commas are not stripped; string returned"),
        ]
        for case in cases:
            with self.subTest(case.description):
                self.assertEqual(case.expected, numberfy(case.arg))

    def test_fails_on_integer(self):
        with self.assertRaises(AttributeError):
            numberfy(123)

    def test_fails_on_float(self):
        with self.assertRaises(AttributeError):
            numberfy(123.45)


class GetApproximateFileSizeInKbTestCase(SimpleTestCase):
    """Tests of the get_approximate_file_size_in_kb function."""

    def test_small_data_returns_minimum(self):
        """Data smaller than 1KB should return the minimum size (1KB by default)."""
        small_data = "x" * 100  # 100 bytes
        result = get_approximate_file_size_in_kb(small_data)
        self.assertEqual(result, "1KB")

    def test_custom_minimum_value(self):
        """Should respect custom minimum value when data is smaller."""
        small_data = "x" * 100  # 100 bytes
        result = get_approximate_file_size_in_kb(small_data, minimum=5)
        self.assertEqual(result, "5KB")

    def test_data_larger_than_minimum(self):
        """Data larger than minimum should return calculated size."""
        # Create data that's approximately 2KB (2048 bytes)
        data = "x" * 2048
        result = get_approximate_file_size_in_kb(data)
        self.assertEqual(result, "2KB")

    def test_rounding_down(self):
        """Should round down when size is closer to lower KB value."""
        # 1280 bytes = 1.25 KB, should round to 1KB
        data = "x" * 1280
        result = get_approximate_file_size_in_kb(data)
        self.assertEqual(result, "1KB")

    def test_rounding_up(self):
        """Should round up when size is closer to higher KB value."""
        # 1792 bytes = 1.75 KB, should round to 2KB
        data = "x" * 1792
        result = get_approximate_file_size_in_kb(data)
        self.assertEqual(result, "2KB")

    def test_large_data(self):
        """Should handle large data correctly."""
        # 50KB of data (51200 bytes)
        data = "x" * 51200
        result = get_approximate_file_size_in_kb(data)
        self.assertEqual(result, "50KB")

    def test_unicode_characters(self):
        """Should handle unicode characters correctly (they use more bytes)."""
        # Unicode characters typically use 2-4 bytes each in UTF-8
        data = "€" * 1024  # Euro symbol, 3 bytes each in UTF-8 = 3072 bytes = 3KB
        result = get_approximate_file_size_in_kb(data)
        self.assertEqual(result, "3KB")

    def test_numeric_input(self):
        """Should handle numeric/list input by converting to string."""
        result = get_approximate_file_size_in_kb([[12345, 67890]])
        self.assertEqual(result, "1KB")
