from typing import Any, ClassVar

from django.test import SimpleTestCase
from wagtail.test.utils import WagtailTestUtils

from cms.datavis.blocks.base import BaseChartBlock, BaseVisualisationBlock
from cms.datavis.tests.factories import TableDataFactory


class BaseVisualisationBlockTestCase(SimpleTestCase, WagtailTestUtils):
    block_type: ClassVar[type[BaseVisualisationBlock]]
    raw_data: dict[str, Any]

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.block = cls.block_type()

    def setUp(self):
        super().setUp()
        self.raw_data = {
            "title": "Test Chart",
            "subtitle": "Test Subtitle",
            "caption": "Test Caption",
            "audio_description": "Test Audio Description",
        }

    def get_value(self, raw_data: dict[str, Any] | None = None):
        if raw_data is None:
            raw_data = self.raw_data
        return self.block.to_python(raw_data)

    def _test_generic_properties(self):
        """Test attributes that are common to all chart blocks."""
        value = self.get_value()
        pairs = [
            # `value` dict key, expected value
            ("title", "Test Chart"),
            ("subtitle", "Test Subtitle"),
            ("audio_description", "Test Audio Description"),
            ("caption", "Test Caption"),
        ]

        for key, expected in pairs:
            with self.subTest(key=key):
                self.assertEqual(expected, value[key])


class BaseChartBlockTestCase(BaseVisualisationBlockTestCase):
    block_type: ClassVar[type[BaseChartBlock]]

    def setUp(self):
        super().setUp()
        self.raw_data.update(
            {
                "table": TableDataFactory(),
                "theme": "primary",
                "show_legend": True,
                "show_data_labels": False,
                "use_stacked_layout": False,
                "show_markers": True,
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
        )

    def get_component_config(self, raw_data: dict[str, Any] | None = None):
        value = self.get_value(raw_data)
        return self.block.get_component_config(value)

    def _test_generic_properties(self):
        """Test attributes that are common to all chart blocks."""
        value = self.get_value()
        pairs = [
            # `value` dict key, expected value
            ("title", "Test Chart"),
            ("subtitle", "Test Subtitle"),
            ("audio_description", "Test Audio Description"),
            ("caption", "Test Caption"),
        ]
        if "theme" in self.block.child_blocks:
            pairs.append(("theme", self.raw_data["theme"]))
        for key, expected in pairs:
            with self.subTest(key=key):
                self.assertEqual(expected, value[key])

        with self.subTest("table"):
            # Test the table_data in the table object is the same.
            # We can't test the whole table object as it is a StructValue, and
            # contains other fields to do with SimpleTable configuration.
            self.assertEqual(self.raw_data["table"]["table_data"], value["table"]["table_data"])

    def _test_get_component_config(self):
        config = self.get_component_config()

        # Test basic structure
        self.assertIn("legend", config)
        self.assertIn("xAxis", config)
        self.assertIn("yAxis", config)
        self.assertIn("series", config)
