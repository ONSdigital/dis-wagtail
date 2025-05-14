from django.test import TestCase
from wagtail.coreutils import get_dummy_request

from cms.articles.tests.factories import ArticleSeriesPageFactory, StatisticalArticlePageFactory
from cms.core.tests.factories import LinkBlockFactory
from cms.navigation.templatetags.navigation_tags import (
    breadcrumbs,
    footer_menu_columns,
    main_menu_columns,
    main_menu_highlights,
)
from cms.navigation.tests.factories import (
    FooterMenuFactory,
    HighlightsBlockFactory,
    LinksColumnFactory,
    MainMenuColumnBlockFactory,
    MainMenuFactory,
    MainMenuSectionBlockFactory,
    TopicLinkBlockFactory,
)


class MainMenuTemplateTagTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.mock_request = get_dummy_request()
        cls.main_menu = MainMenuFactory()

        highlights = [{"type": "highlight", "value": HighlightsBlockFactory()}] * 3

        topic_links = [TopicLinkBlockFactory()] * 5

        sections = [MainMenuSectionBlockFactory(links=topic_links)] * 3

        column_value = MainMenuColumnBlockFactory(sections=sections)

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

        self.assertIsInstance(highlights, list)
        self.assertEqual(len(highlights), 3)

        for highlight in highlights:
            self.assertIn("text", highlight)
            self.assertIn("description", highlight)
            self.assertIn("url", highlight)

    def test_main_menu_columns_output_format(self):
        """Test that main_menu_columns outputs the correct format."""
        columns = main_menu_columns({"request": self.mock_request}, self.main_menu)

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
        cls.mock_request = get_dummy_request()

        links = LinkBlockFactory.create_batch(5)
        columns = [
            {
                "type": "column",
                "value": LinksColumnFactory(links=links),
            }
        ] * 3

        cls.footer_menu = FooterMenuFactory(columns=columns)

    def test_footer_menu_output_format(self):
        """Test that footer_menu outputs the correct format."""
        columns = footer_menu_columns({"request": self.mock_request}, self.footer_menu)

        expected_columns = [
            {
                "title": column.value["title"],
                "itemsList": [
                    {
                        "text": item["title"],
                        "url": item["external_url"],
                    }
                    for item in column.value["links"]
                ],
            }
            for column_index, column in enumerate(self.footer_menu.columns)
        ]

        self.assertIsInstance(columns, list)
        self.assertEqual(len(columns), 3)

        self.assertListEqual(columns, expected_columns)

    def test_footer_menu_empty_menu(self):
        """Test that footer_menu returns an empty list for a None menu."""
        columns = footer_menu_columns({}, None)
        self.assertEqual(columns, [])


class BreadcrumbsTemplateTagTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.mock_request = get_dummy_request()
        cls.series = ArticleSeriesPageFactory()
        cls.statistical_article = StatisticalArticlePageFactory(parent=cls.series)

    def test_breadcrumbs_output_format(self):
        """Test that breadcrumbs outputs the correct format."""
        breadcrumbs_output = breadcrumbs({"request": self.mock_request}, self.statistical_article)

        series_parent = self.series.get_parent()

        expected_entries = [
            {
                "url": "/",
                "text": "Home",
            },
            {
                "url": series_parent.get_parent().get_url(),
                "text": series_parent.get_parent().title,
            },
            {
                "url": series_parent.get_url(),
                "text": series_parent.title,
            },
        ]

        self.assertIsInstance(breadcrumbs_output, list)
        self.assertEqual(len(breadcrumbs_output), 3)
        self.assertListEqual(breadcrumbs_output, expected_entries)
