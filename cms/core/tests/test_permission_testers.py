from django.conf import settings
from django.test import TestCase
from django.urls import reverse
from wagtail.test.utils import WagtailTestUtils

from cms.bundles.tests.utils import grant_all_page_permissions
from cms.core.permission_testers import BasePagePermissionTester
from cms.home.models import HomePage
from cms.users.tests.factories import GroupFactory, UserFactory


class TestBasePagePermissionTester(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.publishing_admin_group = GroupFactory(name="Publishing Admins", access_admin=True)
        grant_all_page_permissions(cls.publishing_admin_group)
        cls.publishing_admin = UserFactory(username="publishing_admin")
        cls.publishing_admin.groups.add(cls.publishing_admin_group)

    def test_can_add_subpage_english(self):
        english_home_page = HomePage.objects.get(locale__language_code=settings.LANGUAGE_CODE)
        tester = BasePagePermissionTester(user=self.publishing_admin, page=english_home_page)
        self.assertTrue(tester.can_add_subpage())

    def test_can_add_subpage_welsh(self):
        welsh_home_page = HomePage.objects.get(locale__language_code="cy")
        tester = BasePagePermissionTester(user=self.publishing_admin, page=welsh_home_page)
        self.assertFalse(tester.can_add_subpage())


class TestCustomPagePermissions(WagtailTestUtils, TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.permission_denied_message = "Sorry, you do not have permission to access this area."

    def setUp(self):
        self.login()

    def test_user_cannot_add_welsh_topic_page_first(self):
        # Creating an information page in Welsh should be forbidden
        # Should only be possible through translating an English page
        welsh_home_page_pk = HomePage.objects.get(locale__language_code="cy").pk
        response = self.client.get(
            reverse("wagtailadmin_pages:add", args=("standard_pages", "informationpage", welsh_home_page_pk)),
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.permission_denied_message)

    def test_user_can_add_english_topic_page_first(self):
        # Creating an English information page should be allowed
        home_page_pk = HomePage.objects.get(locale__language_code=settings.LANGUAGE_CODE).pk
        response = self.client.get(
            reverse("wagtailadmin_pages:add", args=("standard_pages", "informationpage", home_page_pk)),
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, self.permission_denied_message)
