# pylint: disable=too-many-public-methods
from typing import NamedTuple, cast
from unittest import mock

from django.core.exceptions import ValidationError
from wagtail import blocks
from wagtail.blocks.struct_block import StructValue

from cms.datavis.blocks.charts import BarColumnChartBlock
from cms.datavis.constants import BarColumnChartTypeChoices
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
        for chart_type in BarColumnChartTypeChoices.values:
            with self.subTest(chart_type=chart_type):
                data = self.raw_data.copy()
                data["select_chart_type"] = chart_type
                value = self.get_value(data)
                self.assertEqual(chart_type, value.block.get_highcharts_chart_type(value))
                try:
                    self.block.clean(value)
                except ValidationError as e:
                    self.fail(f"ValidationError raised: {e}")

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

    def test_bar_chart_no_x_axis_title(self):
        self.raw_data["select_chart_type"] = BarColumnChartTypeChoices.BAR
        config = self.get_component_config()
        self.assertNotIn("title", config["xAxis"])

    def test_bar_chart_x_axis_title_not_supported(self):
        self.raw_data["select_chart_type"] = BarColumnChartTypeChoices.BAR
        self.raw_data["x_axis"]["title"] = "Editable X-axis Title"
        with self.assertRaises(blocks.StructBlockValidationError) as cm:
            self.block.clean(self.get_value())
        self.assertEqual(
            BarColumnChartBlock.ERROR_HORIZONTAL_BAR_NO_CATEGORY_TITLE,
            cm.exception.block_errors["x_axis"].block_errors["title"].code,
        )

    def test_column_chart_editable_x_axis_title(self):
        self.raw_data["select_chart_type"] = BarColumnChartTypeChoices.COLUMN
        self.raw_data["x_axis"]["title"] = "Editable X-axis Title"
        config = self.get_component_config()
        self.assertEqual("Editable X-axis Title", config["xAxis"]["title"])

    def test_column_chart_blank_x_axis_title(self):
        self.raw_data["select_chart_type"] = BarColumnChartTypeChoices.COLUMN
        self.raw_data["x_axis"]["title"] = ""
        config = self.get_component_config()
        # For column charts, editable X-axis title is supported, but the default
        # value is `undefined`, so we expect it not to be set.
        # Ref: https://api.highcharts.com/highcharts/xAxis.title
        self.assertNotIn("title", config["xAxis"])

    def test_editable_y_axis_title(self):
        for chart_type in BarColumnChartTypeChoices.values:
            with self.subTest(chart_type=chart_type):
                self.raw_data["select_chart_type"] = chart_type
                self.raw_data["y_axis"]["title"] = "Editable Y-axis Title"
                config = self.get_component_config()
                self.assertEqual("Editable Y-axis Title", config["yAxis"]["title"])

    def test_blank_y_axis_title(self):
        """A blank value should be converted to None."""
        for chart_type in BarColumnChartTypeChoices.values:
            with self.subTest(chart_type=chart_type):
                self.raw_data["select_chart_type"] = chart_type
                self.raw_data["y_axis"]["title"] = ""
                config = self.get_component_config()
                self.assertEqual(None, config["yAxis"]["title"])

    def test_show_data_labels(self):
        self.assertEqual(
            2,
            BarColumnChartBlock.MAX_SERIES_COUNT_WITH_DATA_LABELS,
            msg="Max number of series with data labels is hardcoded. Update this test if the value changes.",
        )

        self.assertEqual(
            20,
            BarColumnChartBlock.MAX_DATA_POINTS_WITH_DATA_LABELS,
            msg="Max number of points with data labels is hardcoded. Update this test if the value changes.",
        )

        class Case(NamedTuple):
            chart_type: BarColumnChartTypeChoices
            show_data_labels: bool
            series_count: int
            data_points_count: int
            stacked: bool
            expected_data_labels: bool

        cases = (
            # Data labels are supported on non-stacked bar charts with 1 or 2 series, and a maximum of 20 data points.
            Case(
                BarColumnChartTypeChoices.BAR,
                True,
                1,
                20,
                False,
                True,
            ),
            Case(
                BarColumnChartTypeChoices.BAR,
                True,
                2,
                20,
                False,
                True,
            ),
            # Don't show data labels on stacked bar charts
            Case(
                BarColumnChartTypeChoices.BAR,
                True,
                1,
                20,
                True,
                False,
            ),
            Case(
                BarColumnChartTypeChoices.BAR,
                True,
                2,
                20,
                True,
                False,
            ),
            # Don't show data labels if there are three or more series
            Case(
                BarColumnChartTypeChoices.BAR,
                True,
                3,
                20,
                False,
                False,
            ),
            # Don't show data labels if there are more than 20 data points
            Case(
                BarColumnChartTypeChoices.BAR,
                True,
                1,
                21,
                False,
                False,
            ),
            # Don't show data labels if the option is not checked.
            # The six cases below otherwise repeat the previous six.
            Case(
                BarColumnChartTypeChoices.BAR,
                False,
                1,
                20,
                False,
                False,
            ),
            Case(
                BarColumnChartTypeChoices.BAR,
                False,
                2,
                20,
                False,
                False,
            ),
            Case(
                BarColumnChartTypeChoices.BAR,
                False,
                1,
                20,
                True,
                False,
            ),
            Case(
                BarColumnChartTypeChoices.BAR,
                False,
                2,
                20,
                True,
                False,
            ),
            Case(
                BarColumnChartTypeChoices.BAR,
                False,
                3,
                20,
                False,
                False,
            ),
            Case(
                BarColumnChartTypeChoices.BAR,
                False,
                1,
                21,
                False,
                False,
            ),
            # Don't show data labels on column charts.
            # The six cases below repeat the previous six, but for column charts.
            Case(
                BarColumnChartTypeChoices.COLUMN,
                True,
                1,
                20,
                False,
                False,
            ),
            Case(
                BarColumnChartTypeChoices.COLUMN,
                True,
                2,
                20,
                False,
                False,
            ),
            Case(
                BarColumnChartTypeChoices.COLUMN,
                True,
                1,
                20,
                True,
                False,
            ),
            Case(
                BarColumnChartTypeChoices.COLUMN,
                True,
                2,
                20,
                True,
                False,
            ),
            Case(
                BarColumnChartTypeChoices.COLUMN,
                True,
                3,
                20,
                False,
                False,
            ),
            Case(
                BarColumnChartTypeChoices.COLUMN,
                True,
                1,
                21,
                False,
                False,
            ),
        )

        for testcase in cases:
            with self.subTest(case=testcase):
                self.raw_data["select_chart_type"] = testcase.chart_type
                self.raw_data["show_data_labels"] = testcase.show_data_labels
                self.raw_data["use_stacked_layout"] = testcase.stacked

                # Build the table data
                self.raw_data["table"] = TableDataFactory(
                    table_data=[
                        ["", *[f"Series {i}" for i in range(1, testcase.series_count + 1)]],
                        *[
                            [str(2005 + i), *[str(100 + (i * 20))] * testcase.series_count]
                            for i in range(testcase.data_points_count)
                        ],
                    ]
                )

                config = self.get_component_config()
                for item in config["series"]:
                    match testcase.expected_data_labels:
                        case True:
                            self.assertEqual(True, item["dataLabels"])
                        case False:
                            self.assertNotIn("dataLabels", item)

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
        self.raw_data["select_chart_type"] = BarColumnChartTypeChoices.BAR
        for option in [
            "desktop_aspect_ratio",
            "mobile_aspect_ratio",
        ]:
            with self.subTest(option=option):
                self.raw_data["options"] = [{"type": option, "value": 75}]
                value = self.get_value()

                with self.assertRaises(ValidationError) as cm:
                    self.block.clean(value)

                err = cast(blocks.StructBlockValidationError, cm.exception)
                self.assertEqual(
                    BarColumnChartBlock.ERROR_BAR_CHART_NO_ASPECT_RATIO,
                    err.block_errors["options"].block_errors[0].code,
                )

    def test_column_chart_aspect_ratio_options_are_allowed(self):
        self.raw_data["select_chart_type"] = BarColumnChartTypeChoices.COLUMN
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

    def test_value_axis_min_max_configuration(self):
        """Test that min/max values are correctly configured for the value axis."""
        for chart_type in BarColumnChartTypeChoices.values:
            with self.subTest(chart_type=chart_type):
                self.raw_data["select_chart_type"] = chart_type
                self.raw_data["y_axis"]["min"] = 10.5
                self.raw_data["y_axis"]["max"] = 100.0
                self.block.clean(self.get_value())
                y_axis_config = self.get_value().block.get_component_config(self.get_value())["yAxis"]
                self.assertEqual(10.5, y_axis_config["min"])
                self.assertEqual(100.0, y_axis_config["max"])

    def test_value_axis_start_end_on_tick_defaults(self):
        """Test that start_on_tick and end_on_tick default to False for value axis."""
        for chart_type in BarColumnChartTypeChoices.values:
            with self.subTest(chart_type=chart_type):
                self.raw_data["select_chart_type"] = chart_type
                self.block.clean(self.get_value())
                y_axis_config = self.get_value().block.get_component_config(self.get_value())["yAxis"]
                self.assertEqual(True, y_axis_config["startOnTick"])
                self.assertEqual(True, y_axis_config["endOnTick"])

    def test_value_axis_start_end_on_tick_configuration(self):
        """Test that start_on_tick and end_on_tick can be configured for the value axis."""
        for chart_type in BarColumnChartTypeChoices.values:
            with self.subTest(chart_type=chart_type):
                self.raw_data["select_chart_type"] = chart_type
                self.raw_data["y_axis"]["start_on_tick"] = False
                self.raw_data["y_axis"]["end_on_tick"] = False
                self.block.clean(self.get_value())
                y_axis_config = self.get_value().block.get_component_config(self.get_value())["yAxis"]
                self.assertEqual(False, y_axis_config["startOnTick"])
                self.assertEqual(False, y_axis_config["endOnTick"])

    def test_category_axis_min_max_configuration(self):
        """Test that min/max values are not configured for the category axis."""
        for chart_type in BarColumnChartTypeChoices.values:
            with self.subTest(chart_type=chart_type):
                self.raw_data["select_chart_type"] = chart_type
                self.block.clean(self.get_value())
                x_axis_config = self.get_value().block.get_component_config(self.get_value())["xAxis"]
                self.assertNotIn("min", x_axis_config)
                self.assertNotIn("max", x_axis_config)
                self.assertNotIn("startOnTick", x_axis_config)
                self.assertNotIn("endOnTick", x_axis_config)

    def test_category_axis_start_end_on_tick_defaults(self):
        """Test that start_on_tick and end_on_tick are not configured for category axis."""
        for chart_type in BarColumnChartTypeChoices.values:
            with self.subTest(chart_type=chart_type):
                self.raw_data["select_chart_type"] = chart_type
                self.block.clean(self.get_value())
                x_axis_config = self.get_value().block.get_component_config(self.get_value())["xAxis"]
                self.assertNotIn("startOnTick", x_axis_config)
                self.assertNotIn("endOnTick", x_axis_config)

    def test_category_axis_limits_not_configurable(self):
        for chart_type in BarColumnChartTypeChoices.values:
            with self.subTest(chart_type=chart_type):
                self.raw_data["select_chart_type"] = chart_type
                self.block.clean(self.get_value())
                x_axis_config = self.get_value().block.get_component_config(self.get_value())["xAxis"]
                self.assertNotIn("min", x_axis_config)
                self.assertNotIn("max", x_axis_config)
                self.assertNotIn("startOnTick", x_axis_config)
                self.assertNotIn("endOnTick", x_axis_config)

    def test_custom_reference_line_with_one_series(self):
        self.raw_data["select_chart_type"] = BarColumnChartTypeChoices.COLUMN
        self.raw_data["y_axis"]["custom_reference_line"] = 100
        self.raw_data["table"] = TableDataFactory(
            table_data=[
                ["", "Series 1"],
                ["2005", "100"],
                ["2006", "120"],
                ["2007", "140"],
            ]
        )
        self.block.clean(self.get_value())
        y_axis_config = self.get_value().block.get_component_config(self.get_value())["yAxis"]
        self.assertEqual(100, y_axis_config["customReferenceLineValue"])

    def test_custom_reference_line_not_supported_for_bar_charts(self):
        self.raw_data["select_chart_type"] = BarColumnChartTypeChoices.BAR
        self.raw_data["y_axis"]["custom_reference_line"] = 100
        self.raw_data["table"] = TableDataFactory(
            table_data=[
                ["", "Series 1"],  # only one series
                ["2005", "100"],
                ["2006", "120"],
                ["2007", "140"],
            ]
        )
        with self.assertRaises(blocks.StructBlockValidationError) as cm:
            self.block.clean(self.get_value())
        self.assertEqual(
            BarColumnChartBlock.ERROR_HORIZONTAL_BAR_NO_CUSTOM_REFERENCE_LINE,
            cm.exception.block_errors["y_axis"].block_errors["custom_reference_line"].code,
        )

    def test_custom_reference_line_not_supported_for_multiple_series(self):
        self.raw_data["select_chart_type"] = BarColumnChartTypeChoices.COLUMN
        self.raw_data["y_axis"]["custom_reference_line"] = 100
        self.raw_data["table"] = TableDataFactory(
            table_data=[
                ["", "Series 1", "Series 2"],
                ["2005", "100", "50"],
                ["2006", "120", "55"],
                ["2007", "140", "60"],
            ]
        )
        with self.assertRaises(blocks.StructBlockValidationError) as cm:
            self.block.clean(self.get_value())
        self.assertEqual(
            BarColumnChartBlock.ERROR_MULTIPLE_SERIES_NO_REFERENCE_LINE,
            cm.exception.block_errors["y_axis"].block_errors["custom_reference_line"].code,
        )

    def test_custom_reference_line_not_supported_for_line_overlay(self):
        """Line overlay requires a series, so custom reference line is not supported.

        It's questionable whether this should be allowed, but it's not
        currently. Extra validation would be necessary to permit this.

        This test is to ensure that the tests are updated if this feature is
        supported in future.
        """
        self.raw_data["select_chart_type"] = BarColumnChartTypeChoices.COLUMN
        self.raw_data["use_stacked_layout"] = True
        self.raw_data["y_axis"]["custom_reference_line"] = 100
        self.raw_data["series_customisation"] = [{"type": "series_as_line_overlay", "value": 1}]
        self.raw_data["table"] = TableDataFactory(
            table_data=[
                ["", "Series 1", "Series 2"],
                ["2005", "100", "50"],
                ["2006", "120", "55"],
                ["2007", "140", "60"],
            ]
        )
        with self.assertRaises(blocks.StructBlockValidationError) as cm:
            self.block.clean(self.get_value())
        self.assertEqual(
            BarColumnChartBlock.ERROR_MULTIPLE_SERIES_NO_REFERENCE_LINE,
            cm.exception.block_errors["y_axis"].block_errors["custom_reference_line"].code,
        )


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
        self.raw_data["use_stacked_layout"] = True
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

    def test_unstacked_column_chart_with_more_than_two_series_and_line_overlay_is_not_allowed(self):
        self.raw_data["table"] = TableDataFactory(
            table_data=[
                ["", "Series 1", "Series 2", "Series 3"],
                ["2005", "100", "50", "100"],
                ["2006", "120", "55", "120"],
                ["2007", "140", "60", "140"],
            ]
        )
        self.raw_data["select_chart_type"] = "column"
        self.raw_data["use_stacked_layout"] = False
        self.raw_data["series_customisation"] = [{"type": "series_as_line_overlay", "value": 1}]
        with self.assertRaises(blocks.StructBlockValidationError) as cm:
            self.block.clean(self.get_value())

        self.assertEqual(
            BarColumnChartBlock.ERROR_NON_STACKED_COLUMN_NO_LINE,
            cm.exception.block_errors["series_customisation"].block_errors[0].code,
        )
        # This is the only error
        self.assertEqual(1, len(cm.exception.block_errors))

    def test_unstacked_column_chart_with_two_series_and_line_overlay_is_allowed(self):
        self.raw_data["select_chart_type"] = "column"
        self.raw_data["use_stacked_layout"] = False
        self.raw_data["series_customisation"] = [{"type": "series_as_line_overlay", "value": 1}]
        self.block.clean(self.get_value())

    def test_error_is_raised_if_series_number_is_out_of_range(self):
        self.raw_data["select_chart_type"] = "column"
        self.raw_data["use_stacked_layout"] = True
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
        self.raw_data["use_stacked_layout"] = True
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
        self.raw_data["use_stacked_layout"] = True
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
        self.raw_data["use_stacked_layout"] = True
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
