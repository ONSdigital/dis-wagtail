from django.test import TestCase

from cms.datavis.blocks.table import SimpleTableBlock, SimpleTableStructValue, TableDataType
from cms.datavis.tests.factories import TableDataFactory


class SimpleTableBlockTestCase(TestCase):
    table_data: TableDataType

    def setUp(self):
        self.block = SimpleTableBlock()
        self.block_data = TableDataFactory(
            table_data=[
                ["Header 1", "Header 2", "Header 3"],
                ["Row 1, Column 1", "Row 1, Column 2", "Row 1, Column 3"],
                ["Row 2, Column 1", "Row 2, Column 2", "Row 2, Column 3"],
            ]
        )

    def get_value(self):
        return self.block.to_python(self.block_data)

    def test_the_test_case(self):
        # This is just to test that the test case is working, and has the
        # correct data type
        value = self.get_value()
        self.assertIsInstance(value, SimpleTableStructValue)

    def test_headers(self):
        headers = self.get_value().headers
        self.assertEqual(["Header 1", "Header 2", "Header 3"], headers)

    def test_rows(self):
        value = self.get_value()
        rows = value.rows
        self.assertEqual(
            [
                ["Row 1, Column 1", "Row 1, Column 2", "Row 1, Column 3"],
                ["Row 2, Column 1", "Row 2, Column 2", "Row 2, Column 3"],
            ],
            rows,
        )

    def test_with_empty_table(self):
        self.block_data = TableDataFactory(table_data=[])
        value = self.get_value()

        self.assertEqual([], value.headers)
        self.assertEqual([], value.rows)

    def test_numberfying_numeric_strings(self):
        self.block_data = TableDataFactory(
            table_data=[
                ["Header 1", "Header 2", "Header 3"],
                ["  1", "2  ", "3"],  # Intentional surrounding whitespace
                ["4.0", " 05.07", "6.3"],  # Decimal numbers
            ]
        )
        value = self.get_value()
        self.assertEqual([1, 2, 3], value.rows[0])
        self.assertEqual([4.0, 5.07, 6.3], value.rows[1])
