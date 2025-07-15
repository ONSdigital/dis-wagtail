from wagtail import blocks

from cms.datavis.blocks.annotations import (
    LineAnnotationCategoricalBlock,
    LineAnnotationLinearBlock,
)
from cms.datavis.constants import AxisChoices
from cms.datavis.tests.test_annotations_base import BaseAnnotationTestCase


class GenericLineAnnotationTestCase(BaseAnnotationTestCase):
    block_type = LineAnnotationLinearBlock

    def test_basic(self):
        raw_data = {
            "label": "Nottingham Marjorie",
            "axis": "x",
            "value": 2,
            "label_width": 150,
            "label_offset_x": None,
            "label_offset_y": None,
        }
        try:
            self.block.clean(self.get_value(raw_data))
        except blocks.StructBlockValidationError as e:
            self.fail(f"ValidationError raised: {e.block_errors}")

        config = self.get_config(raw_data)
        self.assertEqual("Nottingham Marjorie", config["text"])
        self.assertEqual(AxisChoices.X, config["axis"])
        self.assertEqual(2, config["value"])
        self.assertEqual(150, config["labelWidth"])
        self.assertNotIn("labelOffsetX", config)
        self.assertNotIn("labelOffsetY", config)

    def test_with_custom_label_positioning(self):
        raw_data = {
            "label": "Strathcarnage",
            "axis": "y",
            "value": 3,
            "label_width": 150,
            "label_offset_x": 100,
            "label_offset_y": 90,
        }

        try:
            self.block.clean(self.get_value(raw_data))
        except blocks.StructBlockValidationError as e:
            self.fail(f"ValidationError raised: {e.block_errors}")

        config = self.get_config(raw_data)
        self.assertEqual("Strathcarnage", config["text"])
        self.assertEqual(AxisChoices.Y, config["axis"])
        self.assertEqual(3, config["value"])
        self.assertEqual(150, config["labelWidth"])
        self.assertEqual(100, config["labelOffsetX"])
        self.assertEqual(-90, config["labelOffsetY"])  # Y-axis is inverted


class LineAnnotationCategoricalTestCase(BaseAnnotationTestCase):
    block_type = LineAnnotationCategoricalBlock

    def test_x_axis_values_must_be_integers(self):
        raw_data = {
            "label": "Taste of Dunfermline",
            "axis": "x",
            "value": 3.5,
            "label_width": 150,
            "label_offset_x": None,
            "label_offset_y": None,
        }
        with self.assertRaises(blocks.StructBlockValidationError) as cm:
            self.block.clean(self.get_value(raw_data))
        self.assertEqual(1, len(cm.exception.block_errors))
        self.assertIn("value", cm.exception.block_errors)
        self.assertEqual(self.block.ERROR_X_AXIS_MUST_BE_INTEGER, cm.exception.block_errors["value"].code)

    def test_x_axis_is_one_indexed(self):
        raw_data = {
            "label": "Taste of Dunfermline",
            "axis": "x",
            "value": 2,
            "label_width": 150,
            "label_offset_x": None,
            "label_offset_y": None,
        }
        try:
            self.block.clean(self.get_value(raw_data))
        except blocks.StructBlockValidationError as e:
            self.fail(f"ValidationError raised: {e.block_errors}")

        config = self.get_config(raw_data)
        self.assertEqual(1, config["value"])  # 1-based UI, 0-based component

    def test_y_axis_value_can_be_float(self):
        raw_data = {
            "label": "Sheffield Bonanza",
            "axis": "y",
            "value": 3.5,
            "label_width": 150,
            "label_offset_x": None,
            "label_offset_y": None,
        }
        try:
            self.block.clean(self.get_value(raw_data))
        except blocks.StructBlockValidationError as e:
            self.fail(f"ValidationError raised: {e.block_errors}")

        config = self.get_config(raw_data)
        self.assertEqual(3.5, config["value"])


class LineAnnotationLinearTestCase(BaseAnnotationTestCase):
    block_type = LineAnnotationLinearBlock

    def test_linear_values(self):
        base_raw_data = {
            "label": "Jam",
            "value": 3.5,
            "label_width": 150,
            "label_offset_x": None,
            "label_offset_y": None,
        }

        for axis in AxisChoices:
            with self.subTest(axis=axis):
                try:
                    self.block.clean(self.get_value({**base_raw_data, "axis": axis.value}))
                except blocks.StructBlockValidationError as e:
                    self.fail(f"ValidationError raised: {e.block_errors}")

                config = self.get_config({**base_raw_data, "axis": axis.value})
                self.assertEqual(3.5, config["value"])
