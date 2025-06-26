# pylint: disable=too-many-public-methods
from typing import cast

from django.core.exceptions import ValidationError
from wagtail import blocks
from wagtail.blocks.struct_block import StructValue

from cms.datavis.blocks.charts import BarColumnConfidenceIntervalChartBlock
from cms.datavis.constants import BarColumnConfidenceIntervalChartTypeChoices
from cms.datavis.tests.factories import TableDataFactory
from cms.datavis.tests.test_chart_blocks_base import BaseChartBlockTestCase


class BarColumnConfidenceIntervalChartBlockTestCase(BaseChartBlockTestCase):
    block_type = BarColumnConfidenceIntervalChartBlock

    def setUp(self):
        super().setUp()
        self.raw_data["table"] = TableDataFactory(
            table_data=[
                ["Category", "Value", "Range min", "Range max"],
                ["2005", "100", "90", "110"],
                ["2006", "120", "110", "130"],
                ["2007", "140", "130", "150"],
            ]
        )
        del self.raw_data["theme"]
        self.raw_data["estimate_line_label"] = "Estimate"
        self.raw_data["uncertainty_range_label"] = "Uncertainty range"

    def test_generic_properties(self):
        self._test_generic_properties()

    def test_get_component_config(self):
        self._test_get_component_config()

    def test_selectable_chart_type(self):
        with self.assertRaises(AttributeError):
            self.block.highcharts_chart_type  # noqa: B018, pylint: disable=pointless-statement
        for chart_type in BarColumnConfidenceIntervalChartTypeChoices.values:
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

    def test_bar_chart_series_data(self):
        """Test bar chart data is formatted correctly.

        Bar chart data should be two series: columnrange for the bars, and
        scatter for the points.
        """
        self.raw_data["select_chart_type"] = BarColumnConfidenceIntervalChartTypeChoices.BAR
        config = self.get_component_config()
        self.assertEqual(2, len(config["series"]))

        # Check uncertainty range series
        self.assertEqual("Uncertainty range", config["series"][0]["name"])
        self.assertEqual([(90, 110), (110, 130), (130, 150)], config["series"][0]["data"])

        # Check estimate line series
        self.assertEqual("Estimate", config["series"][1]["name"])
        self.assertEqual([100, 120, 140], config["series"][1]["data"])
        self.assertTrue(config["series"][1]["marker"])
        self.assertEqual("scatter", config["series"][1]["type"])

    def test_column_chart_series_data(self):
        """Test that column chart data is formatted correctly.

        Column chart data should be one boxplot series for the points, where:
        - min = lower quartile
        - max = upper quartile
        """
        self.raw_data["select_chart_type"] = BarColumnConfidenceIntervalChartTypeChoices.COLUMN
        config = self.get_component_config()
        self.assertEqual(1, len(config["series"]))

        # Check box plot series
        self.assertEqual(
            [(90, 90, 100, 110, 110), (110, 110, 120, 130, 130), (130, 130, 140, 150, 150)],
            config["series"][0]["data"],
        )
        self.assertEqual("Estimate", config["estimateLineLabel"])
        self.assertEqual("Uncertainty range", config["uncertaintyRangeLabel"])

    def test_column_chart_with_no_uncertainty(self):
        """When a datum has no uncertainty range, all five box plot values should be the same."""
        self.raw_data["select_chart_type"] = BarColumnConfidenceIntervalChartTypeChoices.COLUMN
        self.raw_data["table"] = TableDataFactory(
            table_data=[
                ["Category", "Value", "Range min", "Range max"],
                ["2005", "100", "", ""],
                ["2006", "120", "110", "130"],
            ]
        )
        config = self.get_component_config()
        self.assertEqual(
            [(100, 100, 100, 100, 100), (110, 110, 120, 130, 130)],
            config["series"][0]["data"],
        )

    def test_custom_legend_labels(self):
        """Test that custom legend labels are used when provided."""
        self.raw_data["estimate_line_label"] = "Custom Estimate"
        self.raw_data["uncertainty_range_label"] = "Custom Range"

        with self.subTest(chart_type="bar chart"):
            self.raw_data["select_chart_type"] = BarColumnConfidenceIntervalChartTypeChoices.BAR
            config = self.get_component_config()
            self.assertEqual("Custom Estimate", config["series"][1]["name"])
            self.assertEqual("Custom Range", config["series"][0]["name"])

        with self.subTest(chart_type="column chart"):
            self.raw_data["select_chart_type"] = BarColumnConfidenceIntervalChartTypeChoices.COLUMN
            config = self.get_component_config()
            self.assertEqual("Custom Estimate", config["estimateLineLabel"])
            self.assertEqual("Custom Range", config["uncertaintyRangeLabel"])

    def test_unmatched_range_validation(self):
        """Test that validation fails when range values are unmatched."""
        bad_cases = [
            (
                "Missing min",
                TableDataFactory(
                    table_data=[
                        ["Category", "Value", "Range min", "Range max"],
                        ["2005", "100", "", "110"],
                    ]
                ),
            ),
            (
                "Missing max",
                TableDataFactory(
                    table_data=[
                        ["Category", "Value", "Range min", "Range max"],
                        ["2005", "100", "90", ""],
                    ]
                ),
            ),
        ]
        for case, bad_table_data in bad_cases:
            invalid_data = self.raw_data.copy()
            invalid_data["table"] = bad_table_data
            value = self.get_value(invalid_data)
            with self.subTest(bad_case=case):
                with self.assertRaises(blocks.StructBlockValidationError) as cm:
                    self.block.clean(value)

                self.assertEqual(
                    BarColumnConfidenceIntervalChartBlock.ERROR_UNMATCHED_RANGE, cm.exception.block_errors["table"].code
                )

    def test_non_numeric_values_validation(self):
        """Test that validation fails when non-numeric values are present."""
        bad_cases = [
            (
                "non-numeric value",
                TableDataFactory(
                    table_data=[
                        ["Category", "Value", "Range min", "Range max"],
                        ["2005", "eggs", "90", "110"],
                    ]
                ),
            ),
            (
                "non-numeric min",
                TableDataFactory(
                    table_data=[
                        ["Category", "Value", "Range min", "Range max"],
                        ["2005", "100", "fish", "110"],
                    ]
                ),
            ),
            (
                "non-numeric max",
                TableDataFactory(
                    table_data=[
                        ["Category", "Value", "Range min", "Range max"],
                        ["2005", "100", "90", "jam"],
                    ]
                ),
            ),
        ]
        for case, bad_table_data in bad_cases:
            invalid_data = self.raw_data.copy()
            invalid_data["table"] = bad_table_data
            value = self.get_value(invalid_data)
            with self.subTest(bad_case=case):
                with self.assertRaises(blocks.StructBlockValidationError) as cm:
                    self.block.clean(value)
                self.assertEqual(
                    BarColumnConfidenceIntervalChartBlock.ERROR_NON_NUMERIC_VALUE,
                    cm.exception.block_errors["table"].code,
                )

    def test_insufficient_columns_validation(self):
        """Test that validation fails when there are fewer than 4 columns."""
        invalid_data = self.raw_data.copy()
        invalid_data["table"] = TableDataFactory(
            table_data=[
                ["Category", "Value", "Range min"],  # Missing Range max
                ["2005", "100", "90"],
                ["2006", "120", "110"],
                ["2007", "140", "130"],
            ]
        )
        value = self.get_value(invalid_data)
        with self.assertRaises(blocks.StructBlockValidationError) as cm:
            self.block.clean(value)

        self.assertEqual(
            BarColumnConfidenceIntervalChartBlock.ERROR_INSUFFICIENT_COLUMNS, cm.exception.block_errors["table"].code
        )

    def test_bar_chart_aspect_ratio_options_not_allowed(self):
        """Test that aspect ratio options are not allowed for bar charts."""
        self.raw_data["select_chart_type"] = BarColumnConfidenceIntervalChartTypeChoices.BAR
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
                    BarColumnConfidenceIntervalChartBlock.ERROR_BAR_CHART_NO_ASPECT_RATIO,
                    err.block_errors["options"].block_errors[0].code,
                )

    def test_column_chart_aspect_ratio_options_are_allowed(self):
        """Test that aspect ratio options are allowed for column charts."""
        self.raw_data["select_chart_type"] = BarColumnConfidenceIntervalChartTypeChoices.COLUMN
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

    def test_bar_chart_no_x_axis_title(self):
        self.raw_data["select_chart_type"] = BarColumnConfidenceIntervalChartTypeChoices.BAR
        config = self.get_component_config()
        self.assertNotIn("title", config["xAxis"])

    def test_bar_chart_x_axis_title_not_supported(self):
        self.raw_data["select_chart_type"] = BarColumnConfidenceIntervalChartTypeChoices.BAR
        self.raw_data["x_axis"]["title"] = "Editable X-axis Title"
        with self.assertRaises(blocks.StructBlockValidationError) as cm:
            self.block.clean(self.get_value())
        self.assertEqual(
            BarColumnConfidenceIntervalChartBlock.ERROR_HORIZONTAL_BAR_NO_CATEGORY_TITLE,
            cm.exception.block_errors["x_axis"].code,
        )

    def test_column_chart_editable_x_axis_title(self):
        self.raw_data["select_chart_type"] = BarColumnConfidenceIntervalChartTypeChoices.COLUMN
        self.raw_data["x_axis"]["title"] = "Editable X-axis Title"
        config = self.get_component_config()
        self.assertEqual("Editable X-axis Title", config["xAxis"]["title"])

    def test_column_chart_blank_x_axis_title(self):
        self.raw_data["select_chart_type"] = BarColumnConfidenceIntervalChartTypeChoices.COLUMN
        self.raw_data["x_axis"]["title"] = ""
        config = self.get_component_config()
        # For column charts, editable X-axis title is supported, but the default
        # value is `undefined`, so we expect it not to be set.
        # Ref: https://api.highcharts.com/highcharts/xAxis.title
        self.assertNotIn("title", config["xAxis"])

    def test_editable_y_axis_title(self):
        for chart_type in BarColumnConfidenceIntervalChartTypeChoices.values:
            with self.subTest(chart_type=chart_type):
                self.raw_data["select_chart_type"] = chart_type
                self.raw_data["y_axis"]["title"] = "Editable Y-axis Title"
                config = self.get_component_config()
                self.assertEqual("Editable Y-axis Title", config["yAxis"]["title"])

    def test_blank_y_axis_title(self):
        """A blank value should be converted to None."""
        for chart_type in BarColumnConfidenceIntervalChartTypeChoices.values:
            with self.subTest(chart_type=chart_type):
                self.raw_data["select_chart_type"] = chart_type
                self.raw_data["y_axis"]["title"] = ""
                config = self.get_component_config()
                self.assertEqual(None, config["yAxis"]["title"])
