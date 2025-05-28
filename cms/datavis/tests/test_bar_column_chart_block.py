from unittest import mock

from django.core.exceptions import ValidationError
from wagtail import blocks
from wagtail.blocks.struct_block import StructValue

from cms.datavis.blocks.charts import BarColumnChartBlock
from cms.datavis.tests.factories import TableDataFactory
from cms.datavis.tests.test_chart_blocks_base import BaseChartBlockTestCase


class BarColumnChartBlockTestCase(BaseChartBlockTestCase):
    block_type = BarColumnChartBlock

    def setUp(self):
        super().setUp()
        self.raw_data["table"] = TableDataFactory(
            table_data=[
                ["", "Series 1", "Series 2"],
                ["2005", "100", "50"],
                ["2006", "120", "55"],
                ["2007", "140", "60"],
            ]
        )

    def test_generic_properties(self):
        self._test_generic_properties()

    def test_get_component_config(self):
        self._test_get_component_config()

    def test_selectable_chart_type(self):
        with self.assertRaises(AttributeError):
            self.block.highcharts_chart_type  # noqa: B018, pylint: disable=pointless-statement
        for chart_type in ["bar", "column"]:
            with self.subTest(chart_type=chart_type):
                data = self.raw_data.copy()
                data["select_chart_type"] = chart_type
                value = self.get_value(data)
                self.assertEqual(chart_type, value.block.get_highcharts_chart_type(value))

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

    def test_get_single_series_data(self):
        """Test that we identify one series in the data."""
        data = self.raw_data.copy()
        data["table"] = TableDataFactory(
            table_data=[
                ["", "Only one series"],
                ["2005", "100"],
                ["2006", "120"],
                ["2007", "140"],
            ]
        )
        config = self.get_component_config(data)
        self.assertEqual(len(config["series"]), 1)
        self.assertEqual(config["series"][0]["name"], "Only one series")
        self.assertEqual(config["series"][0]["data"], [100, 120, 140])

    def test_get_multiple_series_data(self):
        """Test that we identify two separate series in the data."""
        config = self.get_component_config()
        self.assertEqual(len(config["series"]), 2)
        self.assertEqual(config["series"][0]["name"], "Series 1")
        self.assertEqual(config["series"][0]["data"], [100, 120, 140])
        self.assertEqual(config["series"][1]["name"], "Series 2")
        self.assertEqual(config["series"][1]["data"], [50, 55, 60])

    def test_no_x_axis_title(self):
        config = self.get_component_config()
        self.assertNotIn("title", config["xAxis"])
        # Test again, with title in the data, to prove this is not supported.
        self.raw_data["x_axis"]["title"] = "Editable X-axis Title"
        config = self.get_component_config()
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

    def test_show_data_labels(self):
        for show_data_labels in [False, True]:
            with self.subTest(show_data_labels=show_data_labels):
                self.raw_data["show_data_labels"] = show_data_labels
                config = self.get_component_config()
                for item in config["series"]:
                    self.assertEqual(show_data_labels, item["dataLabels"])

    def test_no_show_markers_option(self):
        """Test that this option is not present for line charts."""
        with self.subTest("base case"):
            config = self.get_component_config()
            for item in config["series"]:
                # Check that we're looking at the right object
                self.assertIn("name", item)
                self.assertIn("data", item)
                self.assertNotIn("marker", item)

        with self.subTest("errantly try to force show_markers to True"):
            # Test that even if we try to pass it in the form cleaned data, it is not in the output.
            self.raw_data["show_markers"] = True
            config = self.get_component_config()
            for item in config["series"]:
                # Check that we're looking at the right object
                self.assertIn("name", item)
                self.assertIn("data", item)
                self.assertNotIn("marker", item)

    def test_bar_chart_aspect_ratio_options_not_allowed(self):
        self.raw_data["select_chart_type"] = "bar"
        for option in [
            "desktop_aspect_ratio",
            "mobile_aspect_ratio",
        ]:
            with self.subTest(option=option):
                self.raw_data["options"] = [{"type": option, "value": 75}]
                value = self.get_value()

                with self.assertRaises(ValidationError) as cm:
                    self.block.clean(value)

                err = cm.exception
                self.assertEqual(
                    BarColumnChartBlock.ERROR_BAR_CHART_NO_ASPECT_RATIO,
                    err.block_errors["options"].block_errors[0].code,
                )

    def test_column_chart_aspect_ratio_options_are_allowed(self):
        self.raw_data["select_chart_type"] = "column"
        for option in [
            "desktop_aspect_ratio",
            "mobile_aspect_ratio",
        ]:
            with self.subTest(option=option):
                self.raw_data["options"] = [{"type": option, "value": 75}]
                value = self.get_value()
                try:
                    self.block.clean(value)
                except ValidationError:
                    self.fail("Expected no ValidationError for column chart aspect ratio options")

    def test_value_axis_tick_interval(self):
        self.raw_data["y_axis"]["tick_interval_mobile"] = 3
        self.raw_data["y_axis"]["tick_interval_desktop"] = 4
        self.block.clean(self.get_value())
        for key, expected in [
            ("tickIntervalMobile", 3),
            ("tickIntervalDesktop", 4),
        ]:
            with self.subTest(key=key):
                self.assertEqual(expected, self.get_value().block.get_component_config(self.get_value())["yAxis"][key])

    def test_category_axis_has_no_tick_interval(self):
        self.raw_data["x_axis"]["tick_interval_mobile"] = 5
        self.raw_data["x_axis"]["tick_interval_desktop"] = 6
        self.block.clean(self.get_value())
        x_axis_config = self.get_value().block.get_component_config(self.get_value())["xAxis"]
        for key in ["tickIntervalMobile", "tickIntervalDesktop"]:
            with self.subTest(key=key):
                self.assertNotIn(key, x_axis_config)


class ColumnChartWithLineTestCase(BaseChartBlockTestCase):
    block_type = BarColumnChartBlock

    def setUp(self):
        super().setUp()
        self.raw_data["table"] = TableDataFactory(
            table_data=[
                ["", "Series 1", "Series 2"],
                ["2005", "100", "50"],
                ["2006", "120", "55"],
                ["2007", "140", "60"],
            ]
        )

    def test_get_series_customisation_is_one_indexed(self):
        with mock.patch.object(self.block, "get_series_customisation") as mock_get_series_customisation:
            mock_get_series_customisation.return_value = {}

            self.block.clean(self.get_value())
            mock_get_series_customisation.assert_has_calls(
                [
                    mock.call(mock.ANY, 1),
                    mock.call(mock.ANY, 2),
                ]
            )

    def test_column_chart_with_one_line_overlay(self):
        self.raw_data["select_chart_type"] = "column"
        self.raw_data["series_customisation"] = [
            {"type": "series_as_line_overlay", "value": 1}  # NB 1-indexed
        ]
        self.block.clean(self.get_value())
        _, series = self.get_value().block.get_series_data(self.get_value())
        # There are two series
        self.assertEqual(2, len(series))
        # The first series is the line overlay
        self.assertEqual("line", series[0]["type"])
        # The second series remains a column
        with self.assertRaises(KeyError):
            # The only supported value for type is "line", when it is omitted we
            # know this is a column.
            series[1]["type"]  # pylint: disable=pointless-statement

    def test_bar_chart_with_line_overlay_is_not_allowed(self):
        self.raw_data["select_chart_type"] = "bar"
        self.raw_data["series_customisation"] = [{"type": "series_as_line_overlay", "value": 1}]
        with self.assertRaises(blocks.StructBlockValidationError) as cm:
            self.block.clean(self.get_value())

        self.assertEqual(
            BarColumnChartBlock.ERROR_HORIZONTAL_BAR_NO_LINE,
            cm.exception.block_errors["series_customisation"].block_errors[0].code,
        )
        # This is the only error
        self.assertEqual(1, len(cm.exception.block_errors))

    def test_horizontal_bar_no_line_error_not_clobbered(self):
        # We don't want particular details about the series number input to hide
        # the fact that this should not be allowed on a bar chart at all.
        self.raw_data["select_chart_type"] = "bar"
        self.raw_data["series_customisation"] = [{"type": "series_as_line_overlay", "value": 10}]  # Out of range
        with self.assertRaises(blocks.StructBlockValidationError) as cm:
            self.block.clean(self.get_value())

        self.assertEqual(
            BarColumnChartBlock.ERROR_HORIZONTAL_BAR_NO_LINE,
            cm.exception.block_errors["series_customisation"].block_errors[0].code,
        )
        # This is the only error
        self.assertEqual(1, len(cm.exception.block_errors))

    def test_error_is_raised_if_series_number_is_out_of_range(self):
        self.raw_data["select_chart_type"] = "column"
        for series_number in [0, 3]:
            with self.subTest(series_number=series_number):
                self.raw_data["series_customisation"] = [
                    {"type": "series_as_line_overlay", "value": series_number},
                ]
                with self.assertRaises(blocks.StructBlockValidationError) as cm:
                    self.block.clean(self.get_value())
                self.assertEqual(
                    BarColumnChartBlock.ERROR_SERIES_OUT_OF_RANGE,
                    cm.exception.block_errors["series_customisation"].block_errors[0].code,
                )
                # This is the only error
                self.assertEqual(1, len(cm.exception.block_errors))

    def test_error_is_raised_if_series_number_is_duplicated(self):
        self.raw_data["select_chart_type"] = "column"
        self.raw_data["series_customisation"] = [
            {"type": "series_as_line_overlay", "value": 1},
            {"type": "series_as_line_overlay", "value": 1},
        ]
        with self.assertRaises(blocks.StructBlockValidationError) as cm:
            self.block.clean(self.get_value())

        self.assertEqual(
            BarColumnChartBlock.ERROR_DUPLICATE_SERIES,
            cm.exception.block_errors["series_customisation"].block_errors[1].code,
        )
        # This is the only error
        self.assertEqual(1, len(cm.exception.block_errors))

    def test_error_is_raised_if_all_series_are_selected_for_line_overlay(self):
        self.raw_data["select_chart_type"] = "column"
        self.raw_data["table"] = TableDataFactory(
            table_data=[
                ["", "Only one series"],
                ["2005", "100"],
                ["2006", "120"],
                ["2007", "140"],
            ]
        )
        self.raw_data["series_customisation"] = [{"type": "series_as_line_overlay", "value": 1}]
        _, series = self.get_value().block.get_series_data(self.get_value())
        # There is one series
        self.assertEqual(1, len(series))
        with self.assertRaises(blocks.StructBlockValidationError) as cm:
            self.block.clean(self.get_value())

        self.assertEqual(
            BarColumnChartBlock.ERROR_ALL_SERIES_SELECTED,
            cm.exception.block_errors["series_customisation"].code,
        )
        # This is the only error
        self.assertEqual(1, len(cm.exception.block_errors))

    def test_all_series_selected_not_raised_for_number_out_of_range(self):
        self.raw_data["select_chart_type"] = "column"
        self.raw_data["series_customisation"] = [
            {"type": "series_as_line_overlay", "value": 1},
            {"type": "series_as_line_overlay", "value": 3},
        ]
        _, series = self.get_value().block.get_series_data(self.get_value())
        # There are two series
        self.assertEqual(2, len(series))
        with self.assertRaises(blocks.StructBlockValidationError) as cm:
            self.block.clean(self.get_value())

        self.assertNotEqual(
            BarColumnChartBlock.ERROR_ALL_SERIES_SELECTED,
            cm.exception.block_errors["series_customisation"].code,
        )
        # This is the only error
        self.assertEqual(1, len(cm.exception.block_errors))
