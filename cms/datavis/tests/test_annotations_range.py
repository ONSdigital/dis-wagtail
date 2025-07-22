from wagtail import blocks

from cms.datavis.blocks.annotations import (
    RangeAnnotationCategoricalBlock,
    RangeAnnotationLinearBlock,
)
from cms.datavis.constants import AxisChoices
from cms.datavis.tests.test_annotations_base import BaseAnnotationTestCase


class GenericRangeAnnotationTestCase(BaseAnnotationTestCase):
    block_type = RangeAnnotationLinearBlock

    def test_basic(self):
        raw_data = {
            "label": "Jam",
            "axis": "x",
            "start_position": 3,
            "end_position": 4,
            "label_inside": False,
            "label_offset_x": None,
            "label_offset_y": None,
            "label_width": None,
        }
        try:
            self.block.clean(self.get_value(raw_data))
        except blocks.StructBlockValidationError as e:
            self.fail(f"ValidationError raised: {e.block_errors}")

        config = self.get_config(raw_data)
        self.assertEqual("Jam", config["text"])
        self.assertFalse(config["labelInside"])
        self.assertEqual(None, config["labelOffsetX"])
        self.assertEqual(None, config["labelOffsetY"])
        self.assertEqual(None, config["labelWidth"])

    def test_with_custom_label_positioning(self):
        raw_data = {
            "label": "Jam",
            "axis": "x",
            "start_position": 3,
            "end_position": 4,
            "label_inside": False,
            "label_offset_x": 100,
            "label_offset_y": 90,
            "label_width": 80,
        }

        try:
            self.block.clean(self.get_value(raw_data))
        except blocks.StructBlockValidationError as e:
            self.fail(f"ValidationError raised: {e.block_errors}")

        config = self.get_config(raw_data)
        self.assertFalse(config["labelInside"])
        self.assertEqual(100, config["labelOffsetX"])
        self.assertEqual(-90, config["labelOffsetY"])
        self.assertEqual(80, config["labelWidth"])

    def test_with_label_inside(self):
        raw_data = {
            "label": "Jam",
            "axis": "x",
            "start_position": 3,
            "end_position": 4,
            "label_inside": True,
            "label_offset_x": None,
            "label_offset_y": None,
            "label_width": None,
        }
        try:
            self.block.clean(self.get_value(raw_data))
        except blocks.StructBlockValidationError as e:
            self.fail(f"ValidationError raised: {e.block_errors}")

        config = self.get_config(raw_data)
        self.assertTrue(config["labelInside"])
        self.assertNotIn("labelOffsetX", config)
        self.assertNotIn("labelOffsetY", config)
        self.assertNotIn("labelWidth", config)

    def test_cannot_customise_label_position_if_label_inside(self):
        raw_data = {
            "label": "Jam",
            "axis": "x",
            "start_position": 3,
            "end_position": 4,
            "label_inside": True,
        }

        for field_name in ["label_offset_x", "label_offset_y", "label_width"]:
            with self.subTest(field=field_name):
                with self.assertRaises(blocks.StructBlockValidationError) as cm:
                    self.block.clean(self.get_value({**raw_data, field_name: 100}))
                self.assertEqual(1, len(cm.exception.block_errors))
                self.assertIn(field_name, cm.exception.block_errors)
                self.assertEqual(
                    self.block.ERROR_LABEL_INSIDE_CUSTOM_POSITIONING, cm.exception.block_errors[field_name].code
                )

    def test_start_position_must_be_less_than_end_position(self):
        raw_data = {
            "label": "Jam",
            "axis": "x",
            "label_inside": True,
        }
        bad_cases = (
            (
                "greater than",
                {
                    "start_position": 4,
                    "end_position": 3,
                },
            ),
            (
                "equal",
                {
                    "start_position": 8,
                    "end_position": 8,
                },
            ),
        )
        for description, data in bad_cases:
            with self.subTest(case=description):
                with self.assertRaises(blocks.StructBlockValidationError) as cm:
                    self.block.clean(self.get_value({**raw_data, **data}))
                self.assertEqual(1, len(cm.exception.block_errors))
                self.assertIn("start_position", cm.exception.block_errors)
                self.assertEqual(self.block.ERROR_ORDERING, cm.exception.block_errors["start_position"].code)


class RangeAnnotationCategoricalTestCase(BaseAnnotationTestCase):
    block_type = RangeAnnotationCategoricalBlock

    def test_x_axis_values_are_discrete(self):
        raw_data = {
            "label": "Jam",
            "axis": "x",
            "start_position": 3,
            "end_position": 4,
            "label_inside": True,
        }
        try:
            self.block.clean(self.get_value(raw_data))
        except blocks.StructBlockValidationError as e:
            self.fail(f"ValidationError raised: {e.block_errors}")

        config = self.get_config(raw_data)

        # Categorical x-axis has 1-indexed UI, but DS expects 0-indexed values
        self.assertEqual(raw_data["start_position"] - 1, config["range"]["axisValue1"])
        self.assertEqual(raw_data["end_position"] - 1, config["range"]["axisValue2"])

    def test_y_axis_values_behave_linearly(self):
        raw_data = {
            "label": "Jam",
            "axis": "y",
            "start_position": -1.5,
            "end_position": 4.2,
            "label_inside": True,
        }
        try:
            self.block.clean(self.get_value(raw_data))
        except blocks.StructBlockValidationError as e:
            self.fail(f"ValidationError raised: {e.block_errors}")

        config = self.get_config(raw_data)

        # Y-axis is always linear, so values should be reported verbatim
        self.assertEqual(raw_data["start_position"], config["range"]["axisValue1"])
        self.assertEqual(raw_data["end_position"], config["range"]["axisValue2"])

    def test_x_axis_must_be_integer(self):
        raw_data = {
            "label": "Jam",
            "axis": "x",
            "start_position": 3.5,
            "end_position": 4,
        }
        with self.assertRaises(blocks.StructBlockValidationError) as cm:
            self.block.clean(self.get_value(raw_data))
        self.assertEqual(1, len(cm.exception.block_errors))
        self.assertIn("start_position", cm.exception.block_errors)
        self.assertEqual(self.block.ERROR_X_AXIS_MUST_BE_INTEGER, cm.exception.block_errors["start_position"].code)


class RangeAnnotationLinearTestCase(BaseAnnotationTestCase):
    block_type = RangeAnnotationLinearBlock

    def test_linear_values(self):
        raw_data = {
            "label": "Jam",
            "start_position": 3,
            "end_position": 4,
            "label_inside": True,
        }

        for axis in AxisChoices:
            with self.subTest(axis=axis):
                try:
                    self.block.clean(self.get_value({**raw_data, "axis": axis.value}))
                except blocks.StructBlockValidationError as e:
                    self.fail(f"ValidationError raised: {e.block_errors}")

                config = self.get_config(raw_data)

                # Coordinate values are always reported verbatim
                self.assertEqual(raw_data["start_position"], config["range"]["axisValue1"])
                self.assertEqual(raw_data["end_position"], config["range"]["axisValue2"])
