from http import HTTPStatus

from django.test import TestCase
from wagtail.rich_text import RichText

from cms.core.permission_testers import BasePagePermissionTester
from cms.themes.tests.factories import ThemePageFactory
from cms.users.tests.factories import UserFactory


class ThemePageTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.page = ThemePageFactory()

    def test_page_content(self):
        response = self.client.get(self.page.url)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertContains(response, self.page.title)
        self.assertInHTML(str(RichText(self.page.summary)), response.content.decode(encoding="utf-8"))

    def test_permission_tester_inherits_from_basepagepermissiontester(self):
        self.assertIsInstance(self.page.permissions_for_user(UserFactory()), BasePagePermissionTester)

    def test_analytics_content_type(self):
        """Test that the GTM content type is 'themes' for top-level theme pages."""
        self.assertEqual(self.page.analytics_content_type, "themes")

    def test_analytics_content_type_sub_theme(self):
        """Test that the GTM content type is 'sub-themes' for sub-theme pages."""
        sub_theme_page = ThemePageFactory(parent=self.page)
        self.assertEqual(sub_theme_page.analytics_content_type, "sub-themes")
