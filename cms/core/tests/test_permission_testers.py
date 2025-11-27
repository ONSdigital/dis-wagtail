from django.conf import settings
from django.test import TestCase

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
