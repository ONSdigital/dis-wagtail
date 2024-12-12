from django.test import TestCase
from cms.navigation.tests.factories import MainMenuFactory
from wagtail.test.utils import WagtailTestUtils


class MainMenuViewTestCase(WagtailTestUtils, TestCase):
    """Test views related to MainMenu."""

    def setUp(self):
        self.main_menu = MainMenuFactory()

    def test_main_menu_rendering(self):
        """Test main menu renders correctly in the frontend."""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Main Menu")
