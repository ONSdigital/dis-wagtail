from django.test import TestCase
from django.urls import reverse
from wagtail.test.utils import WagtailTestUtils
from wagtail.users.models import UserProfile

from cms.users.views import (
    ReadOnlyAvatarSettingsPanel,
    ReadOnlyNameEmailSettingsPanel,
)


class AccountViewPanelsTestCase(WagtailTestUtils, TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = cls.create_superuser(username="admin", password="password")

    def setUp(self):
        self.client.force_login(self.user)
        self.url = reverse("wagtailadmin_account")

    def _get_panels(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        panels = []
        for tab_panels in response.context["panels_by_tab"].values():
            panels.extend(tab_panels)
        return panels

    def test_get_returns_200(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_password_panel_absent(self):
        panels = self._get_panels()
        panel_names = [p.name for p in panels]
        self.assertNotIn("password", panel_names)

    def test_name_email_panel_is_read_only(self):
        panels = self._get_panels()
        name_email_panel = next(p for p in panels if p.name == "name_email")
        self.assertIsInstance(name_email_panel, ReadOnlyNameEmailSettingsPanel)

    def test_avatar_panel_is_read_only(self):
        panels = self._get_panels()
        avatar_panel = next(p for p in panels if p.name == "avatar")
        self.assertIsInstance(avatar_panel, ReadOnlyAvatarSettingsPanel)

    def test_name_email_fields_are_disabled(self):
        panels = self._get_panels()
        name_email_panel = next(p for p in panels if p.name == "name_email")
        form = name_email_panel.get_form()
        for field in form.fields.values():
            self.assertTrue(field.disabled)

    def test_name_not_updated_on_post(self):
        self.user.first_name = "Original"
        self.user.save(update_fields=["first_name"])

        self.client.post(
            self.url,
            {
                "name_email-first_name": "Changed",
                "name_email-last_name": self.user.last_name,
                "name_email-email": self.user.email,
                "theme-theme": "light",
                "theme-contrast": "system",
                "theme-density": "default",
                "theme-keyboard_shortcuts": "false",
                "notifications-approved_notifications": "true",
                "notifications-rejected_notifications": "true",
                "notifications-updated_comments_notifications": "true",
            },
        )

        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, "Original")

    def test_theme_updated_on_post(self):
        profile = UserProfile.get_for_user(self.user)
        self.assertNotEqual(profile.theme, "dark")

        self.client.post(
            self.url,
            {
                "name_email-first_name": self.user.first_name,
                "name_email-last_name": self.user.last_name,
                "name_email-email": self.user.email,
                "theme-theme": "dark",
                "theme-contrast": "system",
                "theme-density": "default",
                "theme-keyboard_shortcuts": "false",
                "notifications-approved_notifications": "true",
                "notifications-rejected_notifications": "true",
                "notifications-updated_comments_notifications": "true",
            },
        )

        profile.refresh_from_db()
        self.assertEqual(profile.theme, "dark")

    def test_avatar_panel_form_never_bound_on_post(self):
        panels = self._get_panels()
        avatar_panel = next(p for p in panels if p.name == "avatar")
        form = avatar_panel.get_form()
        # The form is not bound, i.e. not tied to POST data
        self.assertFalse(form.is_bound)
