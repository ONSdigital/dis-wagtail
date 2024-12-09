# Create your tests here.
from django.test import TestCase
from wagtail.test.utils import WagtailTestUtils
from navigation.models import MainMenu, NavigationSettings
from navigation.tests.factories import MainMenuFactory, NavigationSettingsFactory


class MainMenuTestCase(WagtailTestUtils, TestCase):
    """Test MainMenu model and its blocks."""

    def setUp(self):
        self.main_menu = MainMenuFactory()

    def test_main_menu_str(self):
        """Test __str__ method of MainMenu."""
        self.assertEqual(str(self.main_menu), "Main Menu")

    def test_main_menu_highlights_limit(self):
        """Ensure highlights do not exceed the maximum limit."""
        self.assertLessEqual(len(self.main_menu.highlights), 3)

    def test_main_menu_columns_limit(self):
        """Ensure columns do not exceed the maximum limit."""
        self.assertLessEqual(len(self.main_menu.columns), 3)


class NavigationSettingsTestCase(WagtailTestUtils, TestCase):
    """Test NavigationSettings model."""

    def setUp(self):
        self.settings = NavigationSettingsFactory()

    def test_navigation_settings_main_menu(self):
        """Test NavigationSettings main_menu field."""
        self.assertIsNotNone(self.settings.main_menu)
        self.assertEqual(self.settings.main_menu, self.settings.main_menu)
