from typing import Any, ClassVar

from django.core.exceptions import ValidationError
from django.test import SimpleTestCase
from wagtail.blocks.struct_block import StructValue
from wagtail.test.utils import WagtailTestUtils

from cms.datavis.blocks.base import BaseVisualisationBlock
from cms.datavis.blocks.charts import LineChartBlock
from cms.datavis.tests.factories import TableDataFactory


class BaseChartBlockTestCase(SimpleTestCase, WagtailTestUtils):
    block_type: ClassVar[type[BaseVisualisationBlock]]
    raw_data: dict[str, Any]

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.block = cls.block_type()

    def setUp(self):
        super().setUp()

        self.raw_data = {
            "title": "Test Chart",
            "subtitle": "Test Subtitle",
            "caption": "Test Caption",
            "table": TableDataFactory(),
            "theme": "primary",
            "show_legend": True,
            "show_data_labels": False,
            "use_stacked_layout": False,
            "show_markers": True,
            "x_axis": {
                "label": "",
                "min": None,
                "max": None,
                "tick_interval": None,
            },
            "y_axis": {
                "label": "",
                "min": None,
                "max": None,
                "tick_interval": None,
                "value_suffix": "",
                "tooltip_suffix": "",
            },
            "annotations": [{"type": "point", "value": {"label": "Peak", "x_position": "2", "y_position": "140"}}],
        }

    def get_value(self, raw_data: dict[str, Any] | None = None):
        if raw_data is None:
            raw_data = self.raw_data
        return self.block.to_python(raw_data)

    def _test_generic_properties(self):
        """Test attributes that are common to all chart blocks."""
        value = self.get_value()
        pairs = [
            # `value` dict key, expected value
            ("title", "Test Chart"),
            ("subtitle", "Test Subtitle"),
            ("caption", "Test Caption"),
            ("theme", self.raw_data["theme"]),
        ]
        for key, expected in pairs:
            with self.subTest(key=key):
                self.assertEqual(expected, value[key])

        with self.subTest("table"):
            # Test the table_data in the table object is the same.
            # We can't test the whole table object as it is a StructValue, and
            # contains other fields to do with SimpleTable configuration.
            self.assertEqual(self.raw_data["table"]["table_data"], value["table"]["table_data"])

    def _test_context(self):
        self.assertEqual(
            self.block_type.highcharts_chart_type,
            self.block.get_context(self.get_value())["highcharts_chart_type"],
        )

    def _test_get_component_config(self):
        block_value = self.block.to_python(self.raw_data)
        config = self.block.get_component_config(block_value)

        # Test basic structure
        self.assertIn("legend", config)
        self.assertIn("xAxis", config)
        self.assertIn("yAxis", config)
        self.assertIn("series", config)


class LineChartBlockTestCase(BaseChartBlockTestCase):
    block_type = LineChartBlock

    def setUp(self):
        super().setUp()
        self.raw_data["table"] = TableDataFactory(
            table_data=[
                ["", "Height", "Weight"],
                ["Jan", "100", "50"],
                ["Feb", "120", "55"],
                ["Mar", "140", "60"],
            ]
        )

    def test_generic_properties(self):
        self._test_generic_properties()

    def test_context(self):
        self._test_context()

    def test_get_component_config(self):
        self._test_get_component_config()

    def test_highcharts_chart_type(self):
        context = self.block.get_context(self.get_value())
        self.assertEqual("line", context["highcharts_chart_type"])

    def test_validating_data(self):
        """Test that the data we're using for these unit tests is good."""
        value = self.get_value()
        self.assertIsInstance(value, StructValue)
        try:
            self.block.clean(value)
        except ValidationError as e:
            self.fail(f"ValidationError raised: {e}")

    def test_invalid_data(self):
        """Validate that these tests can detect invalid data."""
        invalid_data = self.raw_data.copy()
        invalid_data["title"] = ""  # Required field
        value = self.get_value(invalid_data)
        with self.assertRaises(ValidationError, msg="Expected ValidationError for missing title"):
            self.block.clean(value)

    def test_get_series_data(self):
        """Test that we identify two separate series in the data."""
        block_value = self.block.to_python(self.raw_data)
        series = self.block.get_series_data(block_value, block_value["table"].headers, block_value["table"].rows)
        self.assertEqual(len(series), 2)
        self.assertEqual(series[0]["name"], "Height")
        self.assertEqual(series[0]["data"], [100, 120, 140])
        self.assertEqual(series[1]["name"], "Weight")
        self.assertEqual(series[1]["data"], [50, 55, 60])

    def test_editable_x_axis_title(self):
        self.raw_data["x_axis"]["title"] = "Editable X-axis Title"
        value = self.get_value()
        self.assertEqual("Editable X-axis Title", value["x_axis"]["title"])

    def test_blank_x_axis_title(self):
        self.raw_data["x_axis"]["title"] = ""
        value = self.get_value()
        self.assertEqual("", value["x_axis"]["title"])

    def test_no_show_data_labels_option(self):
        """Test that this option is not present for line charts."""
        with self.subTest("base case"):
            block_value = self.get_value()
            series = self.block.get_series_data(block_value, block_value["table"].headers, block_value["table"].rows)
            for item in series:
                # Check that we're looking at the right object
                self.assertIn("name", item)
                self.assertIn("data", item)
                self.assertNotIn("dataLabels", item)

        with self.subTest("errantly try to force show_data_labels to True"):
            # Test that even if we try to pass it in the form cleaned data, it is not in the output.
            self.raw_data["show_data_labels"] = True
            block_value = self.get_value()
            series = self.block.get_series_data(block_value, block_value["table"].headers, block_value["table"].rows)
            for item in series:
                # Check that we're looking at the right object
                self.assertIn("name", item)
                self.assertIn("data", item)
                self.assertNotIn("dataLabels", item)

    def test_show_markers(self):
        for show_markers in [False, True]:
            with self.subTest(show_markers=show_markers):
                self.raw_data["show_markers"] = show_markers
                block_value = self.get_value()
                series = self.block.get_series_data(
                    block_value, block_value["table"].headers, block_value["table"].rows
                )
                for item in series:
                    self.assertEqual({"enabled": show_markers}, item["marker"])

    def test_connect_nulls(self):
        block_value = self.get_value()
        series = self.block.get_series_data(block_value, block_value["table"].headers, block_value["table"].rows)
        for item in series:
            self.assertEqual(True, item["connectNulls"])
