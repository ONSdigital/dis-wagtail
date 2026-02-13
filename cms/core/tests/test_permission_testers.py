from datetime import timedelta

from django.conf import settings
from django.contrib.auth.models import Group
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from wagtail.test.utils import WagtailTestUtils

from cms.bundles.enums import BundleStatus
from cms.bundles.tests.factories import BundleFactory, BundlePageFactory
from cms.core.permission_testers import BasePagePermissionTester, StaticPagePermissionTester
from cms.home.models import HomePage
from cms.standard_pages.models import InformationPage
from cms.standard_pages.tests.factories import IndexPageFactory, InformationPageFactory
from cms.users.tests.factories import UserFactory
from cms.workflows.tests.utils import mark_page_as_ready_for_review, mark_page_as_ready_to_publish


class TestBasePagePermissionTester(WagtailTestUtils, TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.publishing_admin = UserFactory(username="publishing_admin")
        cls.publishing_admin.groups.add(Group.objects.get(name=settings.PUBLISHING_ADMINS_GROUP_NAME))
        cls.publishing_officer = UserFactory(username="publishing_officer")
        cls.publishing_officer.groups.add(Group.objects.get(name=settings.PUBLISHING_OFFICERS_GROUP_NAME))
        cls.superuser = cls.create_superuser(username="admin")
        cls.user = UserFactory(access_admin=True, username="non_editor")

        cls.english_home_page = HomePage.objects.get(locale__language_code=settings.LANGUAGE_CODE)
        cls.welsh_home_page = HomePage.objects.get(locale__language_code="cy")
        cls.english_index_page = IndexPageFactory(parent=cls.english_home_page)
        cls.welsh_index_page = IndexPageFactory(parent=cls.welsh_home_page)

        cls.bundle = BundleFactory()

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

    # note: using the index page as it can have children
    def test_can_publish__denied_when_page_in_active_bundle(self):
        BundlePageFactory(parent=self.bundle, page=self.english_index_page)

        for user in [self.superuser, self.publishing_admin, self.publishing_officer, self.user]:
            with self.subTest(f"{user=} cannot publish when page in active bundle"):
                tester = BasePagePermissionTester(user=user, page=self.english_index_page)
                self.assertFalse(tester.can_publish())
                self.assertFalse(tester.can_publish_subpage())

    def test_can_publish__denied_when_no_bundle_but_page_only_in_ready_for_review(self):
        mark_page_as_ready_for_review(self.english_index_page)
        for user in [self.superuser, self.publishing_admin, self.publishing_officer, self.user]:
            with self.subTest(f"{user=} cannot publish when page not ready to publish, outside of bundle"):
                tester = BasePagePermissionTester(user=user, page=self.english_index_page)
                self.assertFalse(tester.can_publish())
                self.assertFalse(tester.can_publish_subpage())

    def test_can_publish__allowed_for_editorial_users_when_no_bundle_but_page_in_ready_to_publish(self):
        mark_page_as_ready_to_publish(self.english_index_page)
        for user in [self.superuser, self.publishing_admin, self.publishing_officer]:
            with self.subTest(f"{user=} can publish when page not ready to publish, outside of bundle"):
                tester = BasePagePermissionTester(user=user, page=self.english_index_page)
                self.assertTrue(tester.can_publish())
                self.assertTrue(tester.can_publish_subpage())

    def test_can_publish__denied_for_non_priviledged_user_when_no_bundle_but_page_in_ready_to_publish(self):
        mark_page_as_ready_to_publish(self.english_index_page)
        tester = BasePagePermissionTester(user=self.user, page=self.english_index_page)
        self.assertFalse(tester.can_publish())
        self.assertFalse(tester.can_publish_subpage())

    def test_can_publish__denied_when_no_active_bundle_or_workflow(self):
        BundlePageFactory(parent=self.bundle, page=self.english_index_page)
        self.bundle.status = BundleStatus.PUBLISHED
        self.bundle.save(update_fields=["status"])

        for user in [self.superuser, self.publishing_admin, self.publishing_officer]:
            with self.subTest(f"{user=} cannot publish when page not ready to publish, with no active bundle"):
                tester = BasePagePermissionTester(user=user, page=self.english_index_page)
                self.assertFalse(tester.can_publish())
                self.assertFalse(tester.can_publish_subpage())

    @override_settings(ALLOW_DIRECT_PUBLISHING_IN_DEVELOPMENT=True)
    def test_can_publish__allowed_for_editorial_users_when_override_setting_says_so(self):
        for user in [self.superuser, self.publishing_admin, self.publishing_officer]:
            with self.subTest(f"{user=} can publish when page not ready to publish, with overrider setting set"):
                tester = BasePagePermissionTester(user=user, page=self.english_index_page)
                self.assertTrue(tester.can_publish())
                self.assertTrue(tester.can_publish_subpage())

    def test_can_unschedule(self):
        go_live_at = timezone.now() + timedelta(minutes=1)
        self.english_index_page.go_live_at = go_live_at
        self.english_index_page.save_revision().publish()

        self.assertTrue(self.english_index_page.approved_schedule)
        self.assertEqual(self.english_index_page.latest_revision.approved_go_live_at, go_live_at)

        for user in [self.superuser, self.publishing_admin, self.publishing_officer]:
            with self.subTest(f"{user=} can unschedule when page scheduled"):
                tester = BasePagePermissionTester(user=user, page=self.english_index_page)
                self.assertTrue(tester.can_unschedule())

    def test_cannot_unschedule__if_no_schedule(self):
        for user in [self.superuser, self.publishing_admin, self.publishing_officer, self.user]:
            with self.subTest(f"{user=} cannot unschedule if no schedule"):
                tester = BasePagePermissionTester(user=user, page=self.english_index_page)
                self.assertFalse(tester.can_unschedule())

    def test_cannot_unschedule__if_in_bundle(self):
        BundlePageFactory(parent=self.bundle, page=self.english_index_page)
        for user in [self.superuser, self.publishing_admin, self.publishing_officer, self.user]:
            with self.subTest(f"{user=} cannot unschedule if page is in bundle"):
                tester = BasePagePermissionTester(user=user, page=self.english_index_page)
                self.assertFalse(tester.can_unschedule())


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


class StaticPagePermissionTesterTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.publishing_admin = UserFactory()
        cls.publishing_admin.groups.add(Group.objects.get(name=settings.PUBLISHING_ADMINS_GROUP_NAME))
        cls.english_home_page = HomePage.objects.get(locale__language_code=settings.LANGUAGE_CODE)
        cls.welsh_home_page = HomePage.objects.get(locale__language_code="cy")

    def test_cannot_change_page(self):
        for method in [
            "can_copy",
            "can_delete",
            "can_unpublish",
            "can_set_view_restrictions",
            "can_move",
        ]:
            with self.subTest(method):
                self.assertFalse(
                    getattr(StaticPagePermissionTester(self.publishing_admin, self.english_home_page), method)()
                )
                self.assertFalse(
                    getattr(StaticPagePermissionTester(self.publishing_admin, self.welsh_home_page), method)()
                )

    def test_cannot_copy_to(self):
        self.assertFalse(
            StaticPagePermissionTester(self.publishing_admin, self.english_home_page).can_copy_to(self.welsh_home_page)
        )
        self.assertFalse(
            StaticPagePermissionTester(self.publishing_admin, self.welsh_home_page).can_copy_to(self.english_home_page)
        )
