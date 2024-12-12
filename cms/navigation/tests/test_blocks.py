from django.test import TestCase
from cms.navigation.tests.factories import (
    MainMenuFactory,
    NavigationSettingsFactory,
    HighlightsBlockFactory,
    ColumnBlockFactory,
    SectionBlockFactory,
)
from wagtail.test.utils import WagtailTestUtils


class MainMenuBlockTestCase(WagtailTestUtils, TestCase):
    """Test custom blocks in MainMenu."""

    def setUp(self):
        self.main_menu = MainMenuFactory()

    def test_highlights_block(self):
        """Test HighlightsBlock properties."""
        for block in self.main_menu.highlights:
            print("block.block_type", block)
            self.assertIn("highlight", block.block_type)
            self.assertTrue(block.value["description"])

    def test_highlights_block_description_length(self):
        """Test that HighlightsBlock enforces max_length on description."""
        for block in self.main_menu.highlights:
            description = block.value["description"]
            self.assertLessEqual(len(description), 50, "Description exceeds max length")

    def test_highlights_streamfield_limit(self):
        """Ensure highlights StreamField does not exceed the maximum limit of 3."""
        highlights = HighlightsBlockFactory.create_batch(4)
        self.main_menu.highlights = highlights
        with self.assertRaises(ValueError):
            self.main_menu.full_clean()

    def test_column_block(self):
        """Test ColumnBlock properties."""
        for column in self.main_menu.columns:
            self.assertIn("column", column.block_type)
            for section in column.value["sections"]:
                self.assertTrue(section.value["section_link"])
                self.assertLessEqual(len(section.value["links"]), 15)

    def test_column_streamfield_limit(self):
        """Ensure columns StreamField does not exceed the maximum limit of 3."""
        columns = ColumnBlockFactory.create_batch(4)
        self.main_menu.columns = columns
        with self.assertRaises(ValueError):
            self.main_menu.full_clean()

    def test_section_block_links_limit(self):
        """Test SectionBlock links do not exceed the maximum limit."""
        for column in self.main_menu.columns:
            for section in column.value["sections"]:
                self.assertLessEqual(len(section.value["links"]), 15, "Section links exceed limit")
