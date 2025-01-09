from django.test import TestCase
from wagtail.test.utils import WagtailTestUtils

from cms.navigation.tests.factories import (
    ColumnBlockFactory,
    HighlightsBlockFactory,
    MainMenuFactory,
    SectionBlockFactory,
)

from django.core.exceptions import ValidationError


class MainMenuBlockTestCase(WagtailTestUtils, TestCase):
    """Test custom blocks in MainMenu."""

    @classmethod
    def setUpTestData(cls):
        cls.main_menu = MainMenuFactory()

    def test_highlights_streamfield_limit(self):
        """Ensure highlights StreamField does not exceed the maximum limit of 3."""
        highlights = [
            {"type": "highlight", "value": HighlightsBlockFactory()},
            {"type": "highlight", "value": HighlightsBlockFactory()},
            {"type": "highlight", "value": HighlightsBlockFactory()},
            {"type": "highlight", "value": HighlightsBlockFactory()},
            {"type": "highlight", "value": HighlightsBlockFactory()},
        ]
        self.main_menu.highlights = highlights

        # print(len(self.main_menu.highlights))

        # Validate the model
        with self.assertRaises(ValidationError) as context:
            self.main_menu.full_clean()  # Calls the model's validation logic

        # print(context.exception.messages)
        self.assertEqual(
            context.exception.messages, ["You cannot have more than 3 highlights. Please remove some items."]
        )

    def test_column_streamfield_limit(self):
        """Ensure columns StreamField does not exceed the maximum limit of 3."""

        # column_block = ColumnBlockFactory()
        # print(column_block["sections"])

        columns = [
            {
                "type": "column",
                "value": ColumnBlockFactory(
                    sections=[SectionBlockFactory(), SectionBlockFactory(), SectionBlockFactory()]
                ),
            },
            {"type": "column", "value": ColumnBlockFactory()},
            {"type": "column", "value": ColumnBlockFactory()},
            {"type": "column", "value": ColumnBlockFactory()},
            {"type": "column", "value": ColumnBlockFactory()},
        ]

        self.main_menu.columns = columns

        # print("Hello", len(self.main_menu.columns))
        # print("Hello 1", columns)
        # print("Hello 2", columns[0]["value"])
        print("Hello 2", columns[0]["value"]["sections"])

        # # Validate the model
        # with self.assertRaises(ValidationError) as context:
        #     self.main_menu.full_clean()  # Calls the model's validation logic

        # self.assertEqual(context.exception.messages, ["Ensure this field has no more than 3 items."])

        # self.assertIn("Ensure this field has no more than 3 items.", str(context.exception))

    # def test_highlights_block(self):
    #     """Ensure highlights StreamField does not exceed the maximum limit of 3."""
    #     # highlights = HighlightsBlockFactory.create_batch(4)
    #     value = {"url": "https://ons.gov.uk", "title": "Highlight", "description": "desc"}
    #     highlights = [
    #         {"type": "highlight", "value": HighlightsBlockFactory()},  # or the dict form
    #         {"type": "highlight", "value": value},
    #         {"type": "highlight", "value": value},
    #         {"type": "highlight", "value": value},
    #     ]
    #     self.main_menu.highlights = highlights
    #     with self.assertRaises(ValueError):
    #         self.main_menu.full_clean()

    def test_column_block(self):
        """Test ColumnBlock properties."""
        for column in self.main_menu.columns:
            self.assertIn("column", column.block_type)
            for section in column.value["sections"]:
                self.assertTrue(section.value["section_link"])
                self.assertLessEqual(len(section.value["links"]), 15)

    def test_highlights_block_description_length(self):
        """Test that HighlightsBlock enforces max_length on description."""
        for block in self.main_menu.highlights:
            description = block.value["description"]
            self.assertLessEqual(len(description), 50, "Description exceeds max length")

    def test_section_block_links_limit(self):
        """Test SectionBlock links do not exceed the maximum limit."""
        for column in self.main_menu.columns:
            for section in column.value["sections"]:
                self.assertLessEqual(len(section.value["links"]), 15, "Section links exceed limit")
