from django.core.exceptions import ValidationError
from wagtail.blocks import StructBlockValidationError
from wagtail.blocks.struct_block import StructValue

from cms.datavis.blocks.charts import AreaChartBlock
from cms.datavis.constants import HighChartsChartType
from cms.datavis.tests.factories import TableDataFactory
from cms.datavis.tests.test_chart_blocks_base import BaseChartBlockTestCase


class AreaChartBlockTestCase(BaseChartBlockTestCase):
    block_type = AreaChartBlock

    def setUp(self):
        super().setUp()
        self.raw_data["table"] = TableDataFactory(
            table_data=[
                ["", "Series 1", "Series 2"],
                ["Q1 2023", "3", "8"],
                ["Q2 2023", "4", "3"],
                ["Q3 2023", "2", "5"],
                ["Q4 2023", "7", "6"],
            ]
        )

    def test_generic_properties(self):
        self._test_generic_properties()

    def test_get_component_config(self):
        self._test_get_component_config()

    def test_highcharts_chart_type(self):
        self.assertEqual(HighChartsChartType.AREA, self.block.highcharts_chart_type)
        value = self.get_value()
        self.assertEqual(HighChartsChartType.AREA, value.block.highcharts_chart_type)

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

    def test_data_with_blanks(self):
        """Test that an error is raised if there are blank cells."""
        empty_cell_data = self.raw_data.copy()
        empty_cell_data["table"] = TableDataFactory(
            table_data=[
                ["Dates", "Series 1", "Series 2"],
                ["Q1 2023", "3", "8"],
                ["Q2 2023", "", "3"],
            ]
        )

        with self.assertRaises(StructBlockValidationError, msg="Expected ValidationError for blank cells") as cm:
            self.block.clean(self.get_value(empty_cell_data))

        self.assertEqual(AreaChartBlock.ERROR_EMPTY_CELLS, cm.exception.block_errors["table"].code)

    def test_editable_x_axis_title(self):
        self.raw_data["x_axis"]["title"] = "Editable X-axis Title"
        config = self.get_component_config()
        self.assertEqual("Editable X-axis Title", config["xAxis"]["title"])

    def test_blank_x_axis_title(self):
        self.raw_data["x_axis"]["title"] = ""
        config = self.get_component_config()
        # For area charts, editable X-axis title is supported, but the default
        # value is `undefined`, so we expect it not to be set.
        # Ref: https://api.highcharts.com/highcharts/xAxis.title
        self.assertNotIn("title", config["xAxis"])

    def test_editable_y_axis_title(self):
        self.raw_data["y_axis"]["title"] = "Editable Y-axis Title"
        config = self.get_component_config()
        self.assertEqual("Editable Y-axis Title", config["yAxis"]["title"])

    def test_blank_y_axis_title(self):
        """A blank value should be converted to None."""
        self.raw_data["y_axis"]["title"] = ""
        config = self.get_component_config()
        self.assertEqual(None, config["yAxis"]["title"])

    def test_y_axis_min_max_configuration(self):
        """Test that min/max values are correctly configured for the y-axis."""
        self.raw_data["y_axis"]["min"] = 0.0
        self.raw_data["y_axis"]["max"] = 150.0
        self.block.clean(self.get_value())
        y_axis_config = self.get_value().block.get_component_config(self.get_value())["yAxis"]
        self.assertEqual(0.0, y_axis_config["min"])
        self.assertEqual(150.0, y_axis_config["max"])

    def test_y_axis_start_end_on_tick_defaults(self):
        """Test that start_on_tick and end_on_tick default to True for y-axis."""
        self.block.clean(self.get_value())
        y_axis_config = self.get_value().block.get_component_config(self.get_value())["yAxis"]
        self.assertEqual(True, y_axis_config["startOnTick"])
        self.assertEqual(True, y_axis_config["endOnTick"])

    def test_y_axis_start_end_on_tick_configuration(self):
        """Test that start_on_tick and end_on_tick can be configured for the y-axis."""
        self.raw_data["y_axis"]["start_on_tick"] = False
        self.raw_data["y_axis"]["end_on_tick"] = False
        self.block.clean(self.get_value())
        y_axis_config = self.get_value().block.get_component_config(self.get_value())["yAxis"]
        self.assertEqual(False, y_axis_config["startOnTick"])
        self.assertEqual(False, y_axis_config["endOnTick"])

    def test_x_axis_min_max_not_configurable(self):
        """Test that min/max values are not configurable for x-axis on area charts."""
        self.block.clean(self.get_value())
        x_axis_config = self.get_value().block.get_component_config(self.get_value())["xAxis"]
        self.assertNotIn("min", x_axis_config)
        self.assertNotIn("max", x_axis_config)
        self.assertNotIn("startOnTick", x_axis_config)
        self.assertNotIn("endOnTick", x_axis_config)
