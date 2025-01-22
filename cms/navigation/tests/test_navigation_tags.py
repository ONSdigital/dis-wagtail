from django.test import TestCase
from unittest.mock import Mock
from cms.navigation.templatetags.navigation_tags import main_menu_highlights, main_menu_columns
from cms.navigation.tests.factories import (
    MainMenuFactory,
    TopicLinkBlockFactory,
    SectionBlockFactory,
    ColumnBlockFactory,
    HighlightsBlockFactory,
)


class MainMenuTemplateTagTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.mock_request = Mock()
        cls.main_menu = MainMenuFactory()

        highlights = [{"type": "highlight", "value": HighlightsBlockFactory()}] * 3

        # Create topic links once if they are identical across sections
        topic_links = [TopicLinkBlockFactory()] * 5

        # Create sections using the pre-defined topic links
        sections = [SectionBlockFactory(links=topic_links)] * 3  # Exceeding limit

        # Create the column value with the sections
        column_value = ColumnBlockFactory(sections=sections)

        # Assemble the columns list with multiple column dictionaries
        columns = [
            {
                "type": "column",
                "value": column_value,
            }
        ] * 3

        cls.main_menu.highlights = highlights
        cls.main_menu.columns = columns

    def test_main_menu_highlights_output_format(self):
        """Test that main_menu_highlights outputs the correct format."""
        highlights = main_menu_highlights({"request": self.mock_request}, self.main_menu)

        self.assertIsInstance(highlights, list)
        self.assertEqual(len(highlights), 3)

        for highlight in highlights:
            self.assertIn("text", highlight)
            self.assertIn("description", highlight)
            self.assertIn("url", highlight)

    def test_main_menu_columns_output_format(self):
        """Test that main_menu_columns outputs the correct format."""
        columns = main_menu_columns({"request": self.mock_request}, self.main_menu)

        self.assertIsInstance(columns, list)
        self.assertEqual(len(columns), 3)

        for column in columns:
            self.assertIn("column", column)
            self.assertIn("linksList", column)
            self.assertIsInstance(column["linksList"], list)

            for section in column["linksList"]:
                self.assertIn("text", section)
                self.assertIn("url", section)
                self.assertIn("children", section)
                self.assertIsInstance(section["children"], list)

                for child in section["children"]:
                    self.assertIn("text", child)
                    self.assertIn("url", child)

    def test_main_menu_highlights_empty_menu(self):
        """Test that main_menu_highlights returns an empty list for a None menu."""
        highlights = main_menu_highlights({}, None)
        self.assertEqual(highlights, [])

    def test_main_menu_columns_empty_menu(self):
        """Test that main_menu_columns returns an empty list for a None menu."""
        columns = main_menu_columns({}, None)
        self.assertEqual(columns, [])
