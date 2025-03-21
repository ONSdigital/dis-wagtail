import collections

from django.test import SimpleTestCase

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
