from django.test import TestCase
from wagtail.test.utils import WagtailTestUtils

from cms.navigation.tests.factories import (
    ColumnBlockFactory,
    HighlightsBlockFactory,
    MainMenuFactory,
    SectionBlockFactory,
    TopicLinkBlockFactory,
    ColumnBlock,
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
        ]  # Exceeding limit
        self.main_menu.highlights = highlights

        print(len(self.main_menu.highlights))

        # Validate the model
        with self.assertRaises(ValidationError) as context:
            self.main_menu.full_clean()  # Calls the model's validation logic

        # print(context.exception.messages)
        self.assertEqual(
            context.exception.messages, ["You cannot have more than 3 highlights. Please remove some items."]
        )

    def test_column_streamfield_limit(self):
        """Ensure columns StreamField does not exceed the maximum limit of 3."""
        # Create topic links once if they are identical across sections
        topic_links = [TopicLinkBlockFactory() for _ in range(15)]

        # Create sections using the pre-defined topic links
        sections = [SectionBlockFactory(links=topic_links) for _ in range(3)]

        # Create the column value with the sections
        column_value = ColumnBlockFactory(sections=sections)

        # Assemble the columns list with multiple column dictionaries
        columns = [
            {
                "type": "column",
                "value": column_value,
            }
            for _ in range(5)  # Exceeding limit
        ]

        self.main_menu.columns = columns

        # print("Hello", len(self.main_menu.columns))
        # print("Hello 1", columns)
        # print("Hello 2", columns[0]["value"])
        # print("Hello 2", columns[0]["value"]["sections"][0]["section_link"]["page"].title)

        # Validate the model
        with self.assertRaises(ValidationError) as context:
            self.main_menu.full_clean()  # Calls the model's validation logic

        self.assertEqual(context.exception.messages, ["You cannot have more than 3 columns. Please remove some items."])

    def test_section_streamfield_limit(self):
        """Ensure sections within a column StreamField do not exceed the maximum limit of 3."""
        # Create topic links once if they are identical across sections
        topic_links = [TopicLinkBlockFactory() for _ in range(1)]

        # Create sections using the pre-defined topic links
        sections = [SectionBlockFactory(links=topic_links) for _ in range(6)]  # Exceeding the limit

        # Create the column value with the sections
        column_value = {
            "type": "column",
            "value": {"sections": sections},  # Mimic StreamField data structure
        }

        # Validate the block manually
        column_block = ColumnBlock()
        with self.assertRaises(ValidationError) as context:
            column_block.clean(column_value["value"])

        self.assertEqual(context.exception.messages, ["You cannot have more than 3 sections in a column."])

        # Assign the column to the main menu and validate the model
        self.main_menu.columns = [column_value] * 3
        with self.assertRaises(ValidationError) as context:
            self.main_menu.full_clean()

        self.assertEqual(context.exception.messages, ["You cannot have more than 3 columns. Please remove some items."])

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
