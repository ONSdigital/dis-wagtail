from wagtail.blocks import StreamValue
from wagtail.test.utils import WagtailTestUtils
from django.test import TestCase
from navigation.models import MainMenu
from navigation.tests.factories import MainMenuFactory


class MainMenuBlockTestCase(WagtailTestUtils, TestCase):
    """Test custom blocks in MainMenu."""

    def setUp(self):
        self.main_menu = MainMenuFactory()

    def test_highlights_block(self):
        """Test HighlightsBlock properties."""
        for block in self.main_menu.highlights:
            self.assertIn("highlight", block.block_type)
            self.assertTrue(block.value["description"])

    def test_column_block(self):
        """Test ColumnBlock properties."""
        for column in self.main_menu.columns:
            self.assertIn("column", column.block_type)
            for section in column.value["sections"]:
                self.assertTrue(section.value["section_link"])
                self.assertLessEqual(len(section.value["links"]), 15)
