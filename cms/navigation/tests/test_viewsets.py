from http import HTTPStatus

from django.test import TestCase
from django.urls import reverse
from wagtail.test.utils import WagtailTestUtils

from cms.navigation.models import MainMenu
from cms.navigation.tests.factories import MainMenuFactory


class MainMenuViewSetTestCase(WagtailTestUtils, TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.superuser = cls.create_superuser(username="admin")

        cls.add_url = reverse("wagtailsnippets_navigation_mainmenu:add")
        cls.dashboard_url = reverse("wagtailadmin_home")

    def setUp(self):
        self.client.force_login(self.superuser)

    def test_main_menu_add_view_can_be_accessed_when_none_exists(self):
        """If no MainMenu exists, the user should be able to access the add view."""
        self.assertEqual(MainMenu.objects.count(), 0, "No MainMenu should exist yet.")
        response = self.client.get(self.add_url)

        self.assertEqual(
            response.status_code, HTTPStatus.OK, "User should be able to access add view when no MainMenu exists."
        )

    def test_main_menu_add_redirects_to_dashboard_when_it_already_exists(self):
        """If a MainMenu already exists, the user should be redirected to the Wagtail dashboard."""
        MainMenuFactory()
        self.assertEqual(MainMenu.objects.count(), 1)

        response = self.client.get(self.add_url)

        self.assertRedirects(
            response,
            self.dashboard_url,
            msg_prefix="User should be redirected to the dashboard if a MainMenu already exists.",
        )
