import wagtail.coreutils
from django.test import TestCase

from cms.core.tests.factories import LinkBlockFactory
from cms.navigation.templatetags.navigation_tags import footer_menu_columns, main_menu_columns, main_menu_highlights
from cms.navigation.tests.factories import (
    ColumnBlockFactory,
    FooterMenuFactory,
    HighlightsBlockFactory,
    LinksColumnFactory,
    MainMenuFactory,
    SectionBlockFactory,
    TopicLinkBlockFactory,
)


class MainMenuTemplateTagTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.mock_request = wagtail.coreutils.get_dummy_request()
        cls.main_menu = MainMenuFactory()

        highlights = [{"type": "highlight", "value": HighlightsBlockFactory()}] * 3
        topic_links = [TopicLinkBlockFactory()] * 5

        sections = [SectionBlockFactory(links=topic_links)] * 3

        column_value = ColumnBlockFactory(sections=sections)

        columns = [
            {
                "type": "column",
                "value": column_value,
            }
        ] * 3

        cls.main_menu.highlights = highlights
        cls.main_menu.columns = columns
        cls.main_menu.save()

    def test_main_menu_highlights_output_format(self):
        """Test that main_menu_highlights outputs the correct format."""
        highlights = main_menu_highlights({"request": self.mock_request}, self.main_menu)
        # print("Type of cls.main_menu:", type(self.main_menu), "which contains: ", self.main_menu)
        # print("Type self.MM:", type(self.main_menu), "self.MM:", self.main_menu)
        # print("Type H col:", type(highlights), "MM columns:", highlights)
        self.assertIsInstance(highlights, list)
        self.assertEqual(len(highlights), 3)

        for highlight in highlights:
            self.assertIn("text", highlight)
            self.assertIn("description", highlight)
            self.assertIn("url", highlight)

    def test_main_menu_columns_output_format(self):
        """Test that main_menu_columns outputs the correct format."""
        columns = main_menu_columns({"request": self.mock_request}, self.main_menu)
        # print("Type self.MM:", type(columns), "self.MM:", self.main_menu)
        # print("Type MM col:", type(columns), "MM columns:", columns)
        expected_columns = [
            {
                "column": column_index,
                "linksList": [
                    {
                        "text": section["section_link"]["title"],
                        "url": section["section_link"]["external_url"],
                        "children": [{"text": link["title"], "url": link["external_url"]} for link in section["links"]],
                    }
                    for section in column.value["sections"]
                ],
            }
            for column_index, column in enumerate(self.main_menu.columns)
        ]

        self.assertIsInstance(columns, list)
        self.assertEqual(len(columns), 3)

        self.assertListEqual(columns, expected_columns)

    def test_main_menu_highlights_empty_menu(self):
        """Test that main_menu_highlights returns an empty list for a None menu."""
        highlights = main_menu_highlights({}, None)
        self.assertEqual(highlights, [])

    def test_main_menu_columns_empty_menu(self):
        """Test that main_menu_columns returns an empty list for a None menu."""
        columns = main_menu_columns({}, None)
        self.assertEqual(columns, [])


class FooterMenuTemplateTagTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.mock_request = wagtail.coreutils.get_dummy_request()

        links_data = [LinkBlockFactory()] * 5
        links_column = LinksColumnFactory(links=links_data)
        columns = [
            {
                "type": "linksColumns",
                "value": links_column,
            }
        ] * 3
        cls.footer_menu = FooterMenuFactory()
        cls.footer_menu.columns = columns
        # cls.footer_menu = FooterMenuFactory(columns = columns)

        print("Footer columns: ", columns)
        print("Type cls.footermenu:", type(cls.footer_menu), "cls.footer_menu includes: ", cls.footer_menu)

    def test_footer_menu_output_format(self):
        """Test that footer_menu outputs the correct format."""
        columns = footer_menu_columns({"request": self.mock_request}, self.footer_menu)
        print(
            "Type self.FM:",
            type(self.footer_menu),
            "self.FM:",
            self.footer_menu,
        )
        print("Type col:", type(columns), "Footer columns:", columns)

    def test_footer_menu_empty_menu(self):
        """Test that footer_menu returns an empty list for a None menu."""
        columns = footer_menu_columns({}, None)
        self.assertEqual(columns, [])
