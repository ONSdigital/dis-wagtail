from http import HTTPStatus

from django.test import TestCase
from django.urls import reverse
from wagtail.test.utils import WagtailTestUtils

from cms.navigation.models import FooterMenu, MainMenu


class MainMenuViewSetTestCase(WagtailTestUtils, TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.superuser = cls.create_superuser(username="admin")

        cls.add_url = reverse("wagtailsnippets_navigation_mainmenu:add")
        cls.dashboard_url = reverse("wagtailadmin_home")

    def setUp(self):
        self.client.force_login(self.superuser)

    def get_main_menu_locales(self):
        return set(MainMenu.objects.values_list("locale__language_code", flat=True))

    def test_main_menu_exists_from_migrations(self):
        """MainMenu should exist because migrations create the default instance and its translation."""
        self.assertEqual(MainMenu.objects.count(), 2, "MainMenu should exist from migrations.")
        self.assertSetEqual(
            self.get_main_menu_locales(), {"en-gb", "cy"}, "Should have one English and one Welsh MainMenu."
        )

    def test_main_menu_add_view_can_be_accessed_when_none_exists(self):
        """If no MainMenu exists, the user should be able to access the add view."""
        MainMenu.objects.all().delete()
        response = self.client.get(self.add_url)

        self.assertEqual(
            response.status_code, HTTPStatus.OK, "User should be able to access add view when no MainMenu exists."
        )

    def test_main_menu_add_redirects_to_dashboard_when_it_already_exists(self):
        """If a MainMenu already exists, the user should be redirected to the Wagtail dashboard."""
        self.assertEqual(MainMenu.objects.count(), 2, "MainMenu should exist from migrations.")
        self.assertSetEqual(
            self.get_main_menu_locales(), {"en-gb", "cy"}, "Should have one English and one Welsh MainMenu."
        )

        response = self.client.get(self.add_url)

        self.assertRedirects(
            response,
            self.dashboard_url,
            msg_prefix="User should be redirected to the dashboard if a MainMenu already exists.",
        )


class FooterMenuViewSetTestCase(WagtailTestUtils, TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.superuser = cls.create_superuser(username="admin")

        cls.add_url = reverse("wagtailsnippets_navigation_footermenu:add")
        cls.dashboard_url = reverse("wagtailadmin_home")

    def setUp(self):
        self.client.force_login(self.superuser)

    def get_footer_menu_locales(self):
        return set(FooterMenu.objects.values_list("locale__language_code", flat=True))

    def test_footer_menu_exists_from_migrations(self):
        """FooterMenu should exist because migrations create the default instance and its translation."""
        self.assertEqual(FooterMenu.objects.count(), 2, "FooterMenu should exist from migrations.")
        self.assertSetEqual(
            self.get_footer_menu_locales(), {"en-gb", "cy"}, "Should have one English and one Welsh FooterMenu."
        )

    def test_footer_menu_add_view_can_be_accessed_when_none_exist(self):
        """If FooterMenu does not exist, the user should be able to access the add view."""
        FooterMenu.objects.all().delete()
        response = self.client.get(self.add_url)

        self.assertEqual(
            response.status_code, HTTPStatus.OK, "User should be able to access add view when no FooterMenu exists."
        )

    def test_footer_menu_add_redirects_to_dashboard_when_it_already_exists(self):
        """If a FooterMenu already exists, the user should be redirected to the Wagtail dashboard."""
        self.assertEqual(FooterMenu.objects.count(), 2, "FooterMenu should exist from migrations.")
        self.assertSetEqual(
            self.get_footer_menu_locales(), {"en-gb", "cy"}, "Should have one English and one Welsh FooterMenu."
        )

        response = self.client.get(self.add_url)

        self.assertRedirects(
            response,
            self.dashboard_url,
            msg_prefix="User should be redirected to the dashboard if a FooterMenu already exists.",
        )
