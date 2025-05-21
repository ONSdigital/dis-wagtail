from typing import Any, ClassVar

from django.test import SimpleTestCase
from wagtail import blocks

from cms.datavis.blocks.annotations import CategoryPointAnnotationBlock, CoordinatePointAnnotationBlock


class BaseAnnotationTestCase(SimpleTestCase):
    block_type: ClassVar[type[blocks.StructBlock]]
    raw_data: dict[str, Any]

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.block = cls.block_type()

    def get_value(self, raw_data: dict[str, Any] | None = None):
        return self.block.to_python(raw_data)

    def get_config(self, raw_data: dict[str, Any] | None = None):
        value = self.get_value(raw_data)
        return value.get_config()


class CategoryPointAnnotationTestCase(BaseAnnotationTestCase):
    block_type = CategoryPointAnnotationBlock

    def test_basic(self):
        config = self.get_config(
            {
                "label": "Water",
                "x_position": 2,
                "y_position": 140,
                "label_offset_x": 100,
                "label_offset_y": 90,
            }
        )
        self.assertEqual("Water", config["text"])
        self.assertEqual(1, config["point"]["x"])  # 1-based UI -> 0-based component
        self.assertEqual(140, config["point"]["y"])
        self.assertEqual(100, config["labelOffsetX"])
        self.assertEqual(-90, config["labelOffsetY"])  # sign inverted

    def test_no_label_offset(self):
        config = self.get_config(
            {
                "label": "Eggnog",
                "x_position": 2,
                "y_position": 140,
            }
        )
        self.assertEqual("Eggnog", config["text"])
        self.assertEqual(1, config["point"]["x"])
        self.assertEqual(140, config["point"]["y"])
        self.assertEqual(None, config["labelOffsetX"])
        self.assertEqual(None, config["labelOffsetY"])

    def test_float_y_position(self):
        config = self.get_config(
            {
                "label": "Radiators",
                "x_position": 2,
                "y_position": 8.5,
            }
        )
        self.assertEqual("Radiators", config["text"])
        self.assertEqual(1, config["point"]["x"])  # 1-based UI -> 0-based component
        self.assertEqual(8.5, config["point"]["y"])


class CoordinatePointAnnotationTestCase(BaseAnnotationTestCase):
    block_type = CoordinatePointAnnotationBlock

    def test_basic(self):
        config = self.get_config(
            {
                "label": "Lights",
                "x_position": 5.5,
                "y_position": 140,
                "label_offset_x": 100,
                "label_offset_y": 90,
            }
        )
        self.assertEqual("Lights", config["text"])
        self.assertEqual(5.5, config["point"]["x"])
        self.assertEqual(140, config["point"]["y"])
        self.assertEqual(100, config["labelOffsetX"])
        self.assertEqual(-90, config["labelOffsetY"])  # sign inverted

    def test_no_label_offset(self):
        config = self.get_config(
            {
                "label": "The Tower of Pisa",
                "x_position": 5.5,
                "y_position": 140,
            }
        )
        self.assertEqual("The Tower of Pisa", config["text"])
        self.assertEqual(5.5, config["point"]["x"])
        self.assertEqual(140, config["point"]["y"])
        self.assertEqual(None, config["labelOffsetX"])
        self.assertEqual(None, config["labelOffsetY"])

    def test_float_y_position(self):
        config = self.get_config(
            {
                "label": "A mountain of cabbages",
                "x_position": 5.5,
                "y_position": 8.5,
            }
        )
        self.assertEqual(8.5, config["point"]["y"])

    def test_negative_x_position(self):
        config = self.get_config(
            {
                "label": "Things that go urgh",
                "x_position": -5.5,
                "y_position": 140,
            }
        )
        self.assertEqual(-5.5, config["point"]["x"])
