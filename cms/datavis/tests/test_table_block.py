from django.test import TestCase

from cms.core.utils import UNWANTED_CONTROL_CHARACTERS
from cms.datavis.blocks.table import SimpleTableBlock, SimpleTableStructValue, TableDataType
from cms.datavis.tests.factories import TableDataFactory


class SimpleTableBlockTestCase(TestCase):
    table_data: TableDataType

    def get_value(self, block_data: dict[str, str]):
        return SimpleTableBlock().to_python(block_data)

    def test_the_test_case(self):
        # This is just to test that the test case is working, and has the
        # correct data type
        block_data = TableDataFactory()
        value = self.get_value(block_data)
        self.assertIsInstance(value, SimpleTableStructValue)

    def test_headers(self):
        block_data = TableDataFactory(
            table_data=[
                ["New header 1", "Uusi header 2", "Header 3 newydd"],
                ["", "", ""],
                ["", "", ""],
            ]
        )
        self.assertEqual(["New header 1", "Uusi header 2", "Header 3 newydd"], self.get_value(block_data).headers)

    def test_rows(self):
        block_data = TableDataFactory(
            table_data=[
                ["light", "air", "fish"],
                ["jam", "soup", "potatoes"],
                ["haircuts", "arguments", "small things"],
            ]
        )
        self.assertEqual(
            [
                ["jam", "soup", "potatoes"],
                ["haircuts", "arguments", "small things"],
            ],
            self.get_value(block_data).rows,
        )

    def test_with_empty_table(self):
        block_data = TableDataFactory(table_data=[])
        value = self.get_value(block_data)

        self.assertEqual([], value.headers)
        self.assertEqual([], value.rows)

    def test_numberfying_numeric_strings(self):
        block_data = TableDataFactory(
            table_data=[
                ["Header 1", "Header 2", "Header 3"],
                ["  1", "2  ", "3"],  # Intentional surrounding whitespace
                ["4.0", " 05.07", "6.3"],  # Decimal numbers
            ]
        )
        value = self.get_value(block_data)
        self.assertEqual([1, 2, 3], value.rows[0])
        self.assertEqual([4.0, 5.07, 6.3], value.rows[1])

    def test_strips_unwanted_control_characters(self):
        block_data = TableDataFactory(
            table_data=[
                ["name", "value"],
                *[["unwanted", char] for char in UNWANTED_CONTROL_CHARACTERS],
            ]
        )
        self.assertEqual(
            self.get_value(block_data).rows,
            [["unwanted", ""]] * len(UNWANTED_CONTROL_CHARACTERS),
        )
        self.assertEqual(
            SimpleTableBlock().clean(block_data).rows,
            [["unwanted", ""]] * len(UNWANTED_CONTROL_CHARACTERS),
        )
