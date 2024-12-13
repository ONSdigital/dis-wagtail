from django.test import TestCase
from wagtail.models import Page
from cms.navigation.models import MainMenu, NavigationSettings
from cms.navigation.tests.factories import (
    MainMenuFactory,
    NavigationSettingsFactory,
    HighlightsBlockFactory,
    SectionBlockFactory,
    ColumnBlockFactory,
    TopicLinkBlockFactory,
)
from django.urls import reverse


# Test for MainMenu model
class MainMenuModelTest(TestCase):
    def test_main_menu_creation(self):
        main_menu = MainMenuFactory()
        self.assertIsInstance(main_menu, MainMenu)
        self.assertEqual(main_menu.highlights.count, 3)
        self.assertEqual(main_menu.columns.count, 3)

    def test_main_menu_str(self):
        main_menu = MainMenuFactory()
        self.assertEqual(str(main_menu), "Main Menu")

    def test_main_menu_highlights_limit(self):
        with self.assertRaises(ValueError):
            MainMenuFactory(highlights=[HighlightsBlockFactory() for _ in range(4)])

    def test_main_menu_columns_limit(self):
        with self.assertRaises(ValueError):
            MainMenuFactory(columns=[ColumnBlockFactory() for _ in range(4)])


# Test for NavigationSettings model
class NavigationSettingsModelTest(TestCase):
    def test_navigation_settings_creation(self):
        navigation_settings = NavigationSettingsFactory()
        self.assertIsInstance(navigation_settings, NavigationSettings)
        self.assertIsInstance(navigation_settings.main_menu, MainMenu)


# Test for HighlightsBlock
class HighlightsBlockTest(TestCase):
    def test_highlights_block(self):
        highlight_block = HighlightsBlockFactory()
        self.assertIn("description", highlight_block)
        self.assertIn("url", highlight_block)
        self.assertIn("title", highlight_block)


# Test for SectionBlock
class SectionBlockTest(TestCase):
    def test_section_block(self):
        section_block = SectionBlockFactory()
        self.assertIn("section_link", section_block)
        self.assertEqual(len(section_block["links"]), 3)

    def test_section_links_limit(self):
        with self.assertRaises(ValueError):
            SectionBlockFactory(links=[TopicLinkBlockFactory() for _ in range(16)])


# Test for ColumnBlock
class ColumnBlockTest(TestCase):
    def test_column_block(self):
        column_block = ColumnBlockFactory()
        self.assertEqual(len(column_block["sections"]), 3)

    def test_column_sections_limit(self):
        with self.assertRaises(ValueError):
            ColumnBlockFactory(sections=[SectionBlockFactory() for _ in range(4)])


# Test for views
class NavigationViewTest(TestCase):
    def setUp(self):
        self.main_menu = MainMenuFactory()
        self.navigation_settings = NavigationSettingsFactory(main_menu=self.main_menu)
        self.home_page = Page.objects.first()

    def test_main_menu_rendering(self):
        response = self.client.get(reverse("wagtail_serve", args=[self.home_page.url]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Main Menu")

    def test_navigation_settings_in_context(self):
        response = self.client.get(reverse("wagtail_serve", args=[self.home_page.url]))
        self.assertEqual(response.status_code, 200)
        self.assertIn("main_menu", response.context)
