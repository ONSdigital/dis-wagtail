from types import NoneType

from django.core.exceptions import ValidationError
from django.test import SimpleTestCase
from wagtail.blocks.struct_block import StructValue

from cms.datavis.blocks.chart_options import AspectRatioBlock
from cms.datavis.blocks.charts import LineChartBlock
from cms.datavis.tests.test_chart_blocks import BaseChartBlockTestCase


class AspectRatioTestCase(SimpleTestCase):
    def test_aspect_ratio_types(self):
        """Test that the block returns an int or None.

        This is only made possible by using TypedChoiceField, hence the
        apparently trivial test.
        """
        block = AspectRatioBlock(required=False)
        for raw_data, expected in [
            (None, NoneType),
            (75, int),
        ]:
            with self.subTest(raw_data=raw_data):
                value = block.field.clean(raw_data)
                self.assertIsInstance(value, expected)


class ChartOptionsTestCase(BaseChartBlockTestCase):
    block_type = LineChartBlock

    def test_no_options_added(self):
        value = self.get_value()
        self.assertEqual(0, len(value.get("options")))
        self.assertEqual({}, value.block.get_additional_options(value))

    def test_one_option_added(self):
        self.raw_data["options"] = [{"type": "desktop_aspect_ratio", "value": 75}]
        value = self.get_value()
        self.assertEqual(1, len(value.get("options", [])))
        self.assertEqual(75, value.get("options", [])[0].value)
        self.assertEqual({"percentageHeightDesktop": 75}, value.block.get_additional_options(value))

    def test_default_value_selected(self):
        self.raw_data["options"] = [{"type": "desktop_aspect_ratio", "value": None}]
        value = self.get_value()
        self.assertEqual(1, len(value.get("options", [])))
        self.assertIsNone(value.get("options", [])[0].value)
        self.assertEqual({"percentageHeightDesktop": None}, value.block.get_additional_options(value))

    def test_setting_multiple_options(self):
        self.raw_data["options"] = [
            {"type": "desktop_aspect_ratio", "value": 75},
            {"type": "mobile_aspect_ratio", "value": 75},
        ]
        value = self.get_value()
        self.assertEqual(2, len(value.get("options", [])))
        self.assertEqual(75, value.get("options", [])[0].value)
        self.assertEqual(
            {"percentageHeightDesktop": 75, "percentageHeightMobile": 75},
            value.block.get_additional_options(value),
        )

    def test_duplicate_options(self):
        self.raw_data["options"] = [
            {"type": "mobile_aspect_ratio", "value": 75},
            {"type": "mobile_aspect_ratio", "value": 75},
        ]
        value = self.get_value()
        self.assertIsInstance(value, StructValue)
        with self.assertRaises(ValidationError, msg="Expected ValidationError for duplicate options"):
            self.block.clean(value)
