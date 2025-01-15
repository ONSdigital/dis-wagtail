from django.test import TestCase
from wagtail.test.utils import WagtailTestUtils

from cms.navigation.tests.factories import (
    ColumnBlockFactory,
    HighlightsBlockFactory,
    MainMenuFactory,
    SectionBlockFactory,
    TopicLinkBlockFactory,
    ThemeLinkBlockFactory,
)

from django.core.exceptions import ValidationError
from wagtail.blocks import StructBlockValidationError
from django.urls import reverse
from wagtail.test.utils.form_data import nested_form_data, streamfield


class MainMenuBlockTestCase(WagtailTestUtils, TestCase):
    """Test custom blocks in MainMenu."""

    @classmethod
    def setUpTestData(cls):
        cls.main_menu = MainMenuFactory()
        cls.user = cls.create_test_user()
        cls.main_menu_edit_url = reverse(
            f"wagtailsnippets_{cls.main_menu._meta.app_label}_{cls.main_menu._meta.model_name}:edit",
            args=[cls.main_menu.pk],
        )

    def test_highlights_streamfield_limit(self):
        """Ensure highlights StreamField does not exceed the maximum limit of 3."""
        self.login(user=self.user)
        form_data = nested_form_data(
            {"highlights": streamfield([("highlight", HighlightsBlockFactory())] * 4), "columns": streamfield([])}
        )

        response = self.client.post(self.main_menu_edit_url, form_data)
        self.assertContains(response, "The maximum number of items is 3")

    def test_column_streamfield_limit(self):
        """Ensure columns StreamField does not exceed the maximum limit of 3."""
        # Create topic links once if they are identical across sections
        topic_links = [TopicLinkBlockFactory()] * 15

        # Create sections using the pre-defined topic links
        sections = [SectionBlockFactory(links=topic_links)] * 3

        # Create the column value with the sections
        column_value = ColumnBlockFactory(sections=sections)

        # Assemble the columns list with multiple column dictionaries
        # columns = [
        #     {
        #         "type": "column",
        #         "value": column_value,
        #     }
        # ] * 4  # Exceeding limit

        self.login(user=self.user)
        form_data = nested_form_data(
            {
                "highlights": streamfield([("highlight", HighlightsBlockFactory())] * 3),
                "columns": streamfield([("column", ColumnBlockFactory())] * 4),
            }
        )

        self.login(user=self.user)

        response = self.client.post(self.main_menu_edit_url, form_data)
        # print("Response", vars(response))
        self.assertContains(response, "The maximum number of items is 3")

    def test_section_streamfield_limit(self):
        """Ensure sections within a column StructBlock do not exceed the maximum limit of 3."""
        # Create topic links once if they are identical across sections
        topic_links = [TopicLinkBlockFactory()] * 15

        # Create sections using the pre-defined topic links
        sections = [SectionBlockFactory(links=topic_links)] * 6  # Exceeding limit

        # Create the column value with the sections
        column_value = ColumnBlockFactory(sections=sections)

        # Assemble the columns list with multiple column dictionaries
        columns = [
            {
                "type": "column",
                "value": column_value,
            }
        ] * 3

        self.main_menu.columns = columns

        # Validate the StreamField blocks explicitly
        for stream_child in self.main_menu.columns:
            print("stream_child", vars(stream_child))
            print("/n")
            block = stream_child.block  # Get the block instance
            print("block", block)
            print("/n")
            value = stream_child.value  # Get the value (data)
            print("value", value)
            print("/n")

            with self.assertRaises(StructBlockValidationError) as context:
                block.clean(value)  # Explicit block validation

            print("Context", vars(context))
            print("Context exception", vars(context.exception))
            print("Context exception block errors", context.exception.block_errors)
            print("Context exception block errors sections", vars(context.exception.block_errors["sections"]))
            print(
                "Context exception block errors sections non block errors",
                context.exception.block_errors["sections"].non_block_errors,
            )
        self.assertListEqual(
            context.exception.block_errors["sections"].non_block_errors, ["The maximum number of items is 3"]
        )

    def test_highlights_block_description_length(self):
        """Test that HighlightsBlock enforces max_length on description for each Highlight."""
        self.login(user=self.user)
        form_data = nested_form_data(
            {
                "highlights": streamfield(
                    [
                        (
                            "highlight",
                            HighlightsBlockFactory(
                                description="This is a random sentence that is exactly sixty characters long."
                            ),
                        )
                    ]
                ),
                "columns": streamfield([]),
            }
        )

        response = self.client.post(self.main_menu_edit_url, form_data)
        print("Response", response)
        self.assertContains(response, "Ensure this value has at most 50 characters (it has 64).")

    def test_column_block(self):
        """Test ColumnBlock properties."""
        for column in self.main_menu.columns:
            self.assertIn("column", column.block_type)
            for section in column.value["sections"]:
                self.assertTrue(section.value["section_link"])
                self.assertLessEqual(len(section.value["links"]), 15)

    def test_section_block_links_limit(self):
        """Test SectionBlock links do not exceed the maximum limit."""
        for column in self.main_menu.columns:
            for section in column.value["sections"]:
                self.assertLessEqual(len(section.value["links"]), 15, "Section links exceed limit")
