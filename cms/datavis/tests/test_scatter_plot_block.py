# pylint: disable=too-many-public-methods
from django.core.exceptions import ValidationError
from wagtail.blocks.struct_block import StructValue

from cms.datavis.blocks.charts import ScatterPlotBlock
from cms.datavis.constants import HighChartsChartType
from cms.datavis.tests.factories import TableDataFactory
from cms.datavis.tests.test_chart_blocks_base import BaseChartBlockTestCase


class ScatterPlotBlockTestCase(BaseChartBlockTestCase):
    block_type = ScatterPlotBlock

    def setUp(self):
        super().setUp()
        self.raw_data = {
            "title": "Test Chart",
            "subtitle": "Test Subtitle",
            "caption": "Test Caption",
            "audio_description": "Test Audio Description",
            "table": TableDataFactory(
                table_data=[
                    ["X", "Y", "Group"],
                    ["1", "2", "First"],
                    ["3", "4", "Second"],
                    ["5", "6", "First"],
                ]
            ),
            "theme": "primary",
            "show_legend": True,
            "show_data_labels": False,
            "use_stacked_layout": False,
            "x_axis": {
                "title": "",
                "min": None,
                "max": None,
                "tick_interval_mobile": None,
                "tick_interval_desktop": None,
            },
            "y_axis": {
                "title": "",
                "min": None,
                "max": None,
                "tick_interval_mobile": None,
                "tick_interval_desktop": None,
                "value_suffix": "",
                "tooltip_suffix": "",
            },
            "annotations": [{"type": "point", "value": {"label": "Peak", "x_position": 2, "y_position": 140}}],
        }

    def test_generic_properties(self):
        self._test_generic_properties()

    def test_get_component_config(self):
        self._test_get_component_config()

    def test_x_axis_min_max_configuration(self):
        """Test that min/max values are correctly configured for the x-axis."""
        self.raw_data["x_axis"]["min"] = 0.5
        self.raw_data["x_axis"]["max"] = 10.0
        self.block.clean(self.get_value())
        x_axis_config = self.get_value().block.get_component_config(self.get_value())["xAxis"]
        self.assertEqual(0.5, x_axis_config["min"])
        self.assertEqual(10.0, x_axis_config["max"])

    def test_y_axis_min_max_configuration(self):
        """Test that min/max values are correctly configured for the y-axis."""
        self.raw_data["y_axis"]["min"] = -5.0
        self.raw_data["y_axis"]["max"] = 50.0
        self.block.clean(self.get_value())
        y_axis_config = self.get_value().block.get_component_config(self.get_value())["yAxis"]
        self.assertEqual(-5.0, y_axis_config["min"])
        self.assertEqual(50.0, y_axis_config["max"])

    def test_x_axis_start_end_on_tick_defaults(self):
        """Test that start_on_tick and end_on_tick default to False for x-axis.

        NB this is the only chart type (at the time of writing) that supports
        min/max values for a Highcharts xAxis (not counting bar chart, where
        Highcharts calls its horizontal value axis the yAxis). Highcharts's
        default start/end-on-tick behaviour for xAxis is False, contrasting
        with True for yAxis.
        """
        self.block.clean(self.get_value())
        x_axis_config = self.get_value().block.get_component_config(self.get_value())["xAxis"]
        self.assertEqual(False, x_axis_config["startOnTick"])
        self.assertEqual(False, x_axis_config["endOnTick"])

    def test_y_axis_start_end_on_tick_defaults(self):
        """Test that start_on_tick and end_on_tick default to True for y-axis."""
        self.block.clean(self.get_value())
        y_axis_config = self.get_value().block.get_component_config(self.get_value())["yAxis"]
        self.assertEqual(True, y_axis_config["startOnTick"])
        self.assertEqual(True, y_axis_config["endOnTick"])

    def test_x_axis_start_end_on_tick_configuration(self):
        """Test that start_on_tick and end_on_tick can be configured for the x-axis."""
        self.raw_data["x_axis"]["start_on_tick"] = False
        self.raw_data["x_axis"]["end_on_tick"] = False
        self.block.clean(self.get_value())
        x_axis_config = self.get_value().block.get_component_config(self.get_value())["xAxis"]
        self.assertEqual(False, x_axis_config["startOnTick"])
        self.assertEqual(False, x_axis_config["endOnTick"])

    def test_y_axis_start_end_on_tick_configuration(self):
        """Test that start_on_tick and end_on_tick can be configured for the y-axis."""
        self.raw_data["y_axis"]["start_on_tick"] = False
        self.raw_data["y_axis"]["end_on_tick"] = False
        self.block.clean(self.get_value())
        y_axis_config = self.get_value().block.get_component_config(self.get_value())["yAxis"]
        self.assertEqual(False, y_axis_config["startOnTick"])
        self.assertEqual(False, y_axis_config["endOnTick"])

    def test_highcharts_chart_type(self):
        self.assertEqual(HighChartsChartType.SCATTER, self.block.highcharts_chart_type)
        value = self.get_value()
        self.assertEqual(HighChartsChartType.SCATTER, value.block.highcharts_chart_type)

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
        self.assertEqual(config["series"][0]["name"], "First")
        self.assertEqual(config["series"][0]["data"], [(1, 2), (5, 6)])
        self.assertEqual(config["series"][1]["name"], "Second")
        self.assertEqual(config["series"][1]["data"], [(3, 4)])

    def test_that_column_headings_are_ignored(self):
        """Test that the data is formatted accordingly even with nonsense headings."""
        self.raw_data["table"] = TableDataFactory(
            table_data=[
                ["Taste of Dunfermline", "Dynamo Aberdaire", "Chunky Norwich"],
                ["1", "4", "Nottingham Marjorie"],
                ["2", "2", "Manchester Coherent"],
                ["1", "2.2", "Manchester Coherent"],
                ["5.9", "1", "Nottingham Marjorie"],
                ["3", "3", "Richmond Arithmetic"],
            ]
        )
        config = self.get_component_config()
        self.assertEqual(len(config["series"]), 3)
        self.assertEqual(config["series"][0]["name"], "Nottingham Marjorie")
        self.assertEqual(config["series"][0]["data"], [(1, 4), (5.9, 1)])
        self.assertEqual(config["series"][1]["name"], "Manchester Coherent")
        self.assertEqual(config["series"][1]["data"], [(2, 2), (1, 2.2)])
        self.assertEqual(config["series"][2]["name"], "Richmond Arithmetic")
        self.assertEqual(config["series"][2]["data"], [(3, 3)])

    def test_subsequent_columns_are_ignored(self):
        """Test that subsequent columns are ignored."""
        self.raw_data["table"] = TableDataFactory(
            table_data=[
                ["X", "Y", "Group", "Extra 1", "Extra 2"],
                ["2.0", "2", "Whomsoever Machine", "good", "2"],
                ["3.2", "1", "Whomsoever Machine", "flappy", "7.2"],
                ["0", "4", "Clerical Explosion", "flimsy", "4"],
                ["3", "4", "Clerical Explosion", "tricky", "foo"],
            ]
        )
        config = self.get_component_config()
        self.assertEqual(len(config["series"]), 2)
        self.assertEqual(config["series"][0]["name"], "Whomsoever Machine")
        self.assertEqual(config["series"][0]["data"], [(2.0, 2), (3.2, 1)])
        self.assertEqual(config["series"][1]["name"], "Clerical Explosion")
        self.assertEqual(config["series"][1]["data"], [(0, 4), (3, 4)])

    def test_data_with_negative_values(self):
        """Test that data with negative values is handled correctly."""
        self.raw_data["table"] = TableDataFactory(
            table_data=[
                ["X", "Y", "Group"],
                ["-1", "2", "First"],
                ["3.2", "-4.8", "First"],
            ]
        )
        config = self.get_component_config()
        self.assertEqual(len(config["series"]), 1)
        self.assertEqual(config["series"][0]["name"], "First")
        self.assertEqual(config["series"][0]["data"], [(-1, 2), (3.2, -4.8)])

    def test_no_show_data_labels_option(self):
        """Test that this option is not present for scatter plots."""
        with self.subTest("base case"):
            config = self.get_component_config()
            for item in config["series"]:
                # Check that we're looking at the right object
                self.assertIn("name", item)
                self.assertIn("data", item)
                self.assertNotIn("dataLabels", item)

    def test_show_markers(self):
        # This is not an editable field, but is set to True in the config.
        self.assertNotIn("show_markers", self.raw_data)
        config = self.get_component_config()
        for item in config["series"]:
            self.assertEqual(True, item["marker"])

    def test_editable_x_axis_title(self):
        self.raw_data["x_axis"]["title"] = "Editable X-axis Title"
        config = self.get_component_config()
        self.assertEqual("Editable X-axis Title", config["xAxis"]["title"])

    def test_blank_x_axis_title(self):
        self.raw_data["x_axis"]["title"] = ""
        config = self.get_component_config()
        # For scatter plots, editable X-axis title is supported, but the default
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
