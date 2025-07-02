# pylint: disable=too-many-public-methods
from django.core.exceptions import ValidationError
from wagtail.blocks.struct_block import StructValue

from cms.datavis.blocks.charts import LineChartBlock
from cms.datavis.constants import HighChartsChartType
from cms.datavis.tests.factories import TableDataFactory
from cms.datavis.tests.test_chart_blocks_base import BaseChartBlockTestCase


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

    def test_get_component_config(self):
        self._test_get_component_config()

    def test_highcharts_chart_type(self):
        self.assertEqual(HighChartsChartType.LINE, self.block.highcharts_chart_type)
        value = self.get_value()
        self.assertEqual(HighChartsChartType.LINE, value.block.highcharts_chart_type)

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

    def test_series_data(self):
        """Test that we identify two separate series in the data."""
        config = self.get_component_config()
        self.assertEqual(len(config["series"]), 2)
        self.assertEqual(config["series"][0]["name"], "Height")
        self.assertEqual(config["series"][0]["data"], [100, 120, 140])
        self.assertEqual(config["series"][1]["name"], "Weight")
        self.assertEqual(config["series"][1]["data"], [50, 55, 60])

    def test_editable_x_axis_title(self):
        self.raw_data["x_axis"]["title"] = "Editable X-axis Title"
        config = self.get_component_config()
        self.assertEqual("Editable X-axis Title", config["xAxis"]["title"])

    def test_blank_x_axis_title(self):
        self.raw_data["x_axis"]["title"] = ""
        config = self.get_component_config()
        # For line charts, editable X-axis title is supported, but the default
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

    def test_no_show_data_labels_option(self):
        """Test that this option is not present for line charts."""
        with self.subTest("base case"):
            config = self.get_component_config()
            for item in config["series"]:
                # Check that we're looking at the right object
                self.assertIn("name", item)
                self.assertIn("data", item)
                self.assertNotIn("dataLabels", item)

        with self.subTest("errantly try to force show_data_labels to True"):
            # Test that even if we try to pass it in the form cleaned data, it is not in the output.
            self.raw_data["show_data_labels"] = True
            config = self.get_component_config()
            for item in config["series"]:
                # Check that we're looking at the right object
                self.assertIn("name", item)
                self.assertIn("data", item)
                self.assertNotIn("dataLabels", item)

    def test_show_markers(self):
        for show_markers in [False, True]:
            with self.subTest(show_markers=show_markers):
                self.raw_data["show_markers"] = show_markers
                config = self.get_component_config()
                for item in config["series"]:
                    self.assertEqual(show_markers, item["marker"])

    def test_connect_nulls(self):
        config = self.get_component_config()
        for item in config["series"]:
            self.assertEqual(True, item["connectNulls"])

    def test_tick_interval_defaults(self):
        self.raw_data["x_axis"]["tick_interval_mobile"] = None
        self.raw_data["x_axis"]["tick_interval_desktop"] = None
        self.raw_data["y_axis"]["tick_interval_mobile"] = None
        self.raw_data["y_axis"]["tick_interval_desktop"] = None
        self.block.clean(self.get_value())
        for axis, key in [
            ("xAxis", "tickIntervalMobile"),
            ("xAxis", "tickIntervalDesktop"),
            ("yAxis", "tickIntervalMobile"),
            ("yAxis", "tickIntervalDesktop"),
        ]:
            with self.subTest(axis=axis, key=key):
                axis_config = self.get_value().block.get_component_config(self.get_value())[axis]
                self.assertNotIn(key, axis_config)

    def test_tick_interval(self):
        self.raw_data["x_axis"]["tick_interval_mobile"] = 1
        self.raw_data["x_axis"]["tick_interval_desktop"] = 2
        self.raw_data["y_axis"]["tick_interval_mobile"] = 3
        self.raw_data["y_axis"]["tick_interval_desktop"] = 4
        self.block.clean(self.get_value())
        for axis, key, expected in [
            ("xAxis", "tickIntervalMobile", 1),
            ("xAxis", "tickIntervalDesktop", 2),
            ("yAxis", "tickIntervalMobile", 3),
            ("yAxis", "tickIntervalDesktop", 4),
        ]:
            with self.subTest(axis=axis, key=key):
                self.assertEqual(expected, self.get_value().block.get_component_config(self.get_value())[axis][key])

    def test_setting_only_one_tick_interval(self):
        self.raw_data["x_axis"]["tick_interval_mobile"] = 5
        self.raw_data["y_axis"]["tick_interval_desktop"] = 10
        self.block.clean(self.get_value())
        config = self.get_value().block.get_component_config(self.get_value())
        for axis, set_key, expected, unset_key in [
            ("xAxis", "tickIntervalMobile", 5, "tickIntervalDesktop"),
            ("yAxis", "tickIntervalDesktop", 10, "tickIntervalMobile"),
        ]:
            with self.subTest(axis=axis, key=set_key, condition="configured"):
                self.assertEqual(expected, config[axis][set_key])
            with self.subTest(axis=axis, key=unset_key, condition="not configured"):
                self.assertNotIn(unset_key, config[axis])

    def test_y_axis_min_max_configuration(self):
        """Test that min/max values are correctly configured for the y-axis."""
        self.raw_data["y_axis"]["min"] = 0.0
        self.raw_data["y_axis"]["max"] = 200.0
        self.block.clean(self.get_value())
        y_axis_config = self.get_value().block.get_component_config(self.get_value())["yAxis"]
        self.assertEqual(0.0, y_axis_config["min"])
        self.assertEqual(200.0, y_axis_config["max"])

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
        """Test that min/max values are not configurable for x-axis on line charts."""
        self.block.clean(self.get_value())
        x_axis_config = self.get_value().block.get_component_config(self.get_value())["xAxis"]
        self.assertNotIn("min", x_axis_config)
        self.assertNotIn("max", x_axis_config)
        self.assertNotIn("startOnTick", x_axis_config)
        self.assertNotIn("endOnTick", x_axis_config)
