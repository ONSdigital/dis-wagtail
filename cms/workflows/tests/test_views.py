from http import HTTPStatus

from django.test import TestCase
from django.urls import reverse
from wagtail.test.utils.wagtail_tests import WagtailTestUtils

from cms.bundles.enums import BundleStatus
from cms.bundles.tests.factories import BundleFactory, BundlePageFactory
from cms.standard_pages.tests.factories import InformationPageFactory
from cms.users.tests.factories import UserFactory
from cms.workflows.models import GroupReviewTask
from cms.workflows.tests.utils import mark_page_as_ready_for_review, mark_page_as_ready_to_publish


class UnlockWorkflowViewTestCase(WagtailTestUtils, TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.bundle = BundleFactory()
        cls.page = InformationPageFactory()

        cls.unlock_url = reverse("workflows:unlock", args=(cls.page.pk,))
        cls.superuser = cls.create_superuser("admin")

    def setUp(self):
        self.client.force_login(self.superuser)

    def test_access__unhappy_paths__bad_page_id(self):
        response = self.client.get(reverse("workflows:unlock", args=(99999,)))
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    def test_access__unhappy_paths__page_not_in_workflow(self):
        response = self.client.get(self.unlock_url, follow=True)
        self.assertContains(response, "Sorry, you do not have permission to access this area.")

    def test_access__unhappy_paths__page_not_ready_to_be_published(self):
        mark_page_as_ready_for_review(self.page)
        response = self.client.get(self.unlock_url, follow=True)
        self.assertContains(response, "Sorry, you do not have permission to access this area.")

    def test_access__unhappy_paths__user_not_in_necessary_group(self):
        generic_user = UserFactory(access_admin=True)

        mark_page_as_ready_for_review(self.page)

        self.client.force_login(generic_user)
        response = self.client.get(self.unlock_url, follow=True)
        self.assertContains(response, "Sorry, you do not have permission to access this area.")

    def test_access__unhappy_paths__page_in_bundle_ready_to_be_published(self):
        mark_page_as_ready_to_publish(self.page)
        BundlePageFactory(parent=self.bundle, page=self.page)
        self.bundle.status = BundleStatus.APPROVED
        self.bundle.save(update_fields=["status"])

        response = self.client.get(self.unlock_url, follow=True)
        self.assertContains(response, "Sorry, you do not have permission to access this area.")

    def _assert_happy_path(self):
        response = self.client.get(self.unlock_url)
        self.assertTemplateUsed(response, "workflows/confirm_unlock.html")
        self.assertContains(
            response,
            "This page is currently ready to be published. Are you sure you want to unlock editing for this page?",
        )

    def test_access__happy_path__page_ready_to_be_published__no_bundle(self):
        mark_page_as_ready_to_publish(self.page)

        self._assert_happy_path()

    def test_access__happy_path__page_ready_to_be_published__in_a_bundle(self):
        mark_page_as_ready_to_publish(self.page)
        BundlePageFactory(parent=self.bundle, page=self.page)

        self._assert_happy_path()

        self.bundle.status = BundleStatus.IN_REVIEW
        self.bundle.save(update_fields=["status"])

        self._assert_happy_path()

    def test_post(self):
        mark_page_as_ready_to_publish(self.page)

        response = self.client.post(self.unlock_url)
        self.assertIsInstance(self.page.current_workflow_task, GroupReviewTask)
        self.assertRedirects(response, reverse("wagtailadmin_pages:edit", args=(self.page.pk,)))
