from django.test import TestCase

from cms.core.permission_testers import BasePagePermissionTester
from cms.themes.tests.factories import ThemePageFactory
from cms.users.tests.factories import UserFactory


class ThemePageTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.page = ThemePageFactory()

    def test_permission_tester_inherits_from_basepagepermissiontester(self):
        self.assertIsInstance(self.page.permissions_for_user(UserFactory()), BasePagePermissionTester)

    def test_analytics_content_type(self):
        """Test that the GTM content type is 'themes' for top-level theme pages."""
        self.assertEqual(self.page.analytics_content_type, "themes")

    def test_analytics_content_type_sub_theme(self):
        """Test that the GTM content type is 'sub-themes' for sub-theme pages."""
        sub_theme_page = ThemePageFactory(parent=self.page)
        self.assertEqual(sub_theme_page.analytics_content_type, "sub-themes")
