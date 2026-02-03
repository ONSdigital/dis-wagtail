from django.conf import settings
from django.test import TestCase
from django.urls import reverse
from wagtail.test.utils import WagtailTestUtils

from cms.bundles.tests.utils import grant_all_page_permissions
from cms.core.permission_testers import BasePagePermissionTester
from cms.home.models import HomePage
from cms.standard_pages.models import InformationPage
from cms.standard_pages.tests.factories import IndexPageFactory, InformationPageFactory
from cms.users.tests.factories import GroupFactory, UserFactory


class TestBasePagePermissionTester(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.publishing_admin_group = GroupFactory(name="Publishing Admins", access_admin=True)
        grant_all_page_permissions(cls.publishing_admin_group)
        cls.publishing_admin = UserFactory(username="publishing_admin")
        cls.publishing_admin.groups.add(cls.publishing_admin_group)
        cls.english_home_page = HomePage.objects.get(locale__language_code=settings.LANGUAGE_CODE)
        cls.welsh_home_page = HomePage.objects.get(locale__language_code="cy")
        cls.english_index_page = IndexPageFactory(parent=cls.english_home_page)
        cls.welsh_index_page = IndexPageFactory(parent=cls.welsh_home_page)

    def test_can_add_subpage_english(self):
        tester = BasePagePermissionTester(user=self.publishing_admin, page=self.english_home_page)
        self.assertTrue(tester.can_add_subpage())

    def test_can_add_subpage_welsh(self):
        """Test that can_add_subpage returns False for a Welsh page."""
        tester = BasePagePermissionTester(user=self.publishing_admin, page=self.welsh_home_page)
        self.assertFalse(tester.can_add_subpage())

    def test_can_copy_english(self):
        english_info_page = InformationPageFactory(parent=self.english_index_page)
        tester = BasePagePermissionTester(user=self.publishing_admin, page=english_info_page)
        self.assertTrue(tester.can_copy())

    def test_can_copy_welsh(self):
        """Test that can_copy returns False for a Welsh page."""
        welsh_info_page = InformationPageFactory(parent=self.welsh_index_page)
        tester = BasePagePermissionTester(user=self.publishing_admin, page=welsh_info_page)
        self.assertFalse(tester.can_copy())


class TestCustomPagePermissions(WagtailTestUtils, TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.permission_denied_message = "Sorry, you do not have permission to access this area."
        cls.english_home_page = HomePage.objects.get(locale__language_code=settings.LANGUAGE_CODE)
        cls.welsh_home_page = HomePage.objects.get(locale__language_code="cy")
        cls.english_index_page = IndexPageFactory(parent=cls.english_home_page)
        cls.welsh_index_page = IndexPageFactory(parent=cls.welsh_home_page)

    def setUp(self):
        self.login()

    def test_user_cannot_add_welsh_topic_page_first(self):
        # Creating an information page in Welsh should be forbidden
        # Should only be possible through translating an English page
        welsh_index_page_pk = self.welsh_index_page.pk
        response = self.client.get(
            reverse("wagtailadmin_pages:add", args=("standard_pages", "informationpage", welsh_index_page_pk)),
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.permission_denied_message)

    def test_user_can_add_english_topic_page_first(self):
        # Creating an English information page should be allowed
        index_page_pk = self.english_index_page.pk
        response = self.client.get(
            reverse("wagtailadmin_pages:add", args=("standard_pages", "informationpage", index_page_pk)),
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, self.permission_denied_message)

    def test_user_cannot_copy_welsh_page(self):
        welsh_info_page = InformationPageFactory(
            parent=self.welsh_index_page,
        )
        new_slug = welsh_info_page.slug + "-copy"
        response = self.client.post(
            reverse("wagtailadmin_pages:copy", args=(welsh_info_page.pk,)),
            data={
                "new_title": welsh_info_page.title + " Copy",
                "new_slug": welsh_info_page,
                "new_parent_page": welsh_info_page.get_parent().pk,
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "You do not have permission")
        with self.assertRaises(InformationPage.DoesNotExist):
            InformationPage.objects.get(slug=new_slug)

    def test_user_can_copy_english_page(self):
        english_info_page = InformationPageFactory(
            parent=self.english_index_page,
        )
        new_slug = english_info_page.slug + "-copy"
        new_title = english_info_page.title + " Copy"
        response = self.client.post(
            reverse("wagtailadmin_pages:copy", args=(english_info_page.pk,)),
            data={"new_title": new_title, "new_slug": new_slug, "new_parent_page": english_info_page.get_parent().pk},
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        new_copy_page = InformationPage.objects.get(slug=new_slug)
        self.assertEqual(new_copy_page.title, new_title)
        self.assertEqual(new_copy_page.get_parent().pk, english_info_page.get_parent().pk)
