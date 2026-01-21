from unittest.mock import patch

from django.conf import settings
from django.contrib.auth.models import Group
from django.test import TestCase
from django.urls import reverse
from wagtail.admin.action_menu import PageLockedMenuItem
from wagtail.test.utils.form_data import nested_form_data, rich_text, streamfield
from wagtail.test.utils.wagtail_tests import WagtailTestUtils

from cms.articles.tests.factories import StatisticalArticlePageFactory
from cms.bundles.enums import BundleStatus
from cms.bundles.tests.factories import BundleFactory, BundlePageFactory
from cms.core.permission_testers import BasePagePermissionTester
from cms.home.models import HomePage
from cms.users.tests.factories import UserFactory
from cms.workflows.locks import PageReadyToBePublishedLock
from cms.workflows.models import GroupReviewTask, ReadyToPublishGroupTask
from cms.workflows.tests.utils import (
    mark_page_as_ready_for_review,
    mark_page_as_ready_to_publish,
    progress_page_workflow,
)
from cms.workflows.utils import is_page_ready_to_publish


class WorkflowTweaksTestCase(WagtailTestUtils, TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.publishing_admin = UserFactory()
        cls.publishing_admin.groups.add(Group.objects.get(name=settings.PUBLISHING_ADMINS_GROUP_NAME))
        cls.publishing_officer = UserFactory()
        cls.publishing_officer.groups.add(Group.objects.get(name=settings.PUBLISHING_OFFICERS_GROUP_NAME))

        cls.page = StatisticalArticlePageFactory()
        cls.edit_url = reverse("wagtailadmin_pages:edit", args=[cls.page.id])

        cls.bundle = BundleFactory()
        cls.bundle_page = BundlePageFactory(parent=cls.bundle, page=cls.page)

    def mark_bundle_as_ready_to_publish(self):
        # mark the bundle as ready to publish
        self.bundle.status = BundleStatus.APPROVED
        self.bundle.save(update_fields=["status"])

    def assertActionIn(self, action, menu_items):  # pylint: disable=invalid-name
        actions = {item.name for item in menu_items}
        self.assertIn(action, actions)

    def assertActionNotIn(self, action, menu_items):  # pylint: disable=invalid-name
        actions = {item.name for item in menu_items}
        self.assertNotIn(action, actions)

    def test_amend_page_action_menu_items_hook(self):
        # Mark the page as ready for review
        mark_page_as_ready_for_review(self.page, self.publishing_admin)

        # Log in as publishing_admin (who was the last editor)
        self.client.force_login(self.publishing_admin)
        response = self.client.get(self.edit_url)

        self.assertNotContains(response, 'data-workflow-action-name="approve"')
        self.assertNotContains(response, "Approve")
        self.assertNotContains(response, "Approve with comment")

        # Log in as the second user (who was not the last editor)
        self.client.force_login(self.publishing_officer)
        response = self.client.get(self.edit_url)

        self.assertContains(response, 'data-workflow-action-name="approve"')
        self.assertContains(response, "Approve")
        self.assertContains(response, "Approve with comment")

    def test_cancel_workflow_action_menu_item(self):
        # Log in as publishing_admin (who was the last editor)
        self.client.force_login(self.publishing_admin)

        # Mark the page as ready for review
        workflow_state = mark_page_as_ready_for_review(self.page, self.publishing_admin)

        response = self.client.get(self.edit_url)
        self.assertContains(response, 'name="action-cancel-workflow"')

        # ready to publish, but not in a bundle
        progress_page_workflow(workflow_state)
        response = self.client.get(self.edit_url)
        self.assertContains(response, 'name="action-cancel-workflow"')

        # add to bundle
        BundlePageFactory(parent=self.bundle, page=self.page)
        response = self.client.get(self.edit_url)
        self.assertContains(response, 'name="action-cancel-workflow"')

        self.mark_bundle_as_ready_to_publish()

        response = self.client.get(self.edit_url)
        self.assertNotContains(response, 'name="action-cancel-workflow"')

    def test_before_edit_page(self):
        """Test that users cannot self-approve their changes."""
        # Log in as publishing_admin
        self.client.force_login(self.publishing_admin)

        mark_page_as_ready_for_review(self.page, self.publishing_admin)
        latest_revision = self.page.latest_revision

        data = nested_form_data(
            {
                "title": self.page.title,
                "slug": self.page.slug,
                "summary": rich_text(self.page.summary),
                "main_points_summary": rich_text(self.page.main_points_summary),
                "release_date": self.page.release_date,
                "content": streamfield(
                    [("section", {"title": "Test", "content": streamfield([("rich_text", rich_text("text"))])})]
                ),
                "headline_figures": streamfield([]),
                "datasets": streamfield([]),
                "dataset_sorting": "AS_SHOWN",
                "corrections": streamfield([]),
                "notices": streamfield([]),
                "action-workflow-action": "true",
                "workflow-action-name": "approve",
                "featured_chart": streamfield([]),
            }
        )
        response = self.client.post(self.edit_url, data, follow=True)

        self.assertContains(
            response, "Cannot self-approve your changes. Please ask another Publishing team member to do so."
        )
        self.page.refresh_from_db()
        self.assertEqual(self.page.latest_revision.pk, latest_revision.pk)

        # Now test with publishing_officer
        self.client.force_login(self.publishing_officer)

        response = self.client.post(self.edit_url, data, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Cannot self-approve your changes")

        self.assertTrue(is_page_ready_to_publish(self.page))
        self.page.refresh_from_db()
        self.assertEqual(self.page.latest_revision.user_id, self.publishing_officer.id)
        self.assertNotEqual(self.page.latest_revision.pk, latest_revision.pk)

    def test_workflow_task_can_unlock(self):
        review_task = GroupReviewTask()
        ready_to_publish_task = ReadyToPublishGroupTask()

        self.assertTrue(review_task.user_can_unlock(self.page, self.publishing_admin))
        self.assertTrue(ready_to_publish_task.user_can_unlock(self.page, self.publishing_admin))
        self.assertFalse(review_task.user_can_unlock(self.page, self.publishing_officer))
        self.assertFalse(ready_to_publish_task.user_can_unlock(self.page, self.publishing_officer))

    def test_workflow_task_ready_to_publish_locked_for_user(self):
        workflow_state = mark_page_as_ready_to_publish(self.page)
        task: ReadyToPublishGroupTask = workflow_state.current_task_state.task

        self.assertTrue(task.locked_for_user(self.page, self.publishing_admin))
        self.assertTrue(task.locked_for_user(self.page, self.publishing_officer))

    def test_workflow_task_ready_to_publish_locked_for_user_when_page_in_bundle_ready_to_be_published(self):
        workflow_state = mark_page_as_ready_to_publish(self.page)

        bundle = BundleFactory(approved=True, publication_date=None)
        BundlePageFactory(parent=bundle, page=self.page)

        task: ReadyToPublishGroupTask = workflow_state.current_task_state.task

        self.assertTrue(task.locked_for_user(self.page, self.publishing_admin))
        self.assertTrue(task.locked_for_user(self.page, self.publishing_officer))

    def test_get_lock(self):
        self.assertIsNotNone(self.page.get_lock)

        mark_page_as_ready_to_publish(self.page)
        self.assertIsNotNone(self.page.get_lock)

        self.mark_bundle_as_ready_to_publish()

        self.assertIsInstance(self.page.get_lock(), PageReadyToBePublishedLock)

    def test_page_locked_if_in_bundle_ready_to_be_published(self):
        self.client.force_login(self.publishing_admin)
        self.assertIsNotNone(self.page.get_lock)

        mark_page_as_ready_to_publish(self.page)
        self.mark_bundle_as_ready_to_publish()

        response = self.client.get(self.edit_url)
        bundle_url = reverse("bundle:edit", args=[self.bundle.pk])
        self.assertContains(
            response,
            "This page is included in a bundle that is ready to be published. You must revert the bundle to "
            "<strong>Draft</strong> or <strong>In preview</strong> in order to make further changes. "
            '<span class="buttons"><a type="button" class="button button-small button-secondary" '
            f'href="{bundle_url}">Manage bundle</a></span>',
        )

        self.assertContains(
            response,
            f'You must revert the bundle "<a href="{bundle_url}">{self.bundle.name}</a>" to <strong>Draft</strong> or '
            f'<strong>In preview</strong> in order to make further changes. <a href="{bundle_url}">Manage bundle</a>.',
        )

    @patch("cms.workflows.locks.user_can_manage_bundles", return_value=False)
    @patch("cms.bundles.panels.user_can_manage_bundles", return_value=False)
    def test_page_locked_if_in_bundle_ready_to_be_published_but_user_cannot_manage_bundles(self, _mock, _mock2):
        self.client.force_login(self.publishing_admin)

        # note: we are mocking user_can_manage_bundles in all entry points.
        mark_page_as_ready_to_publish(self.page)
        self.mark_bundle_as_ready_to_publish()

        response = self.client.get(self.edit_url)
        self.assertContains(
            response,
            "This page cannot be changed as it included "
            f'in the "{self.bundle.name}" bundle which is ready to be published.',
        )
        self.assertNotContains(response, "Manage bundle")
        self.assertNotContains(response, reverse("bundle:edit", args=[self.bundle.pk]))

    def test_ready_to_publish_task__get_actions__user_can_publish__non_bundle_page(self):
        non_bundle_page = StatisticalArticlePageFactory()
        mark_page_as_ready_to_publish(non_bundle_page)

        self.assertEqual(
            non_bundle_page.current_workflow_task.get_actions(non_bundle_page, self.publishing_admin),
            [("unlock", "Unlock editing", False), ("locked-approve", "Approve", False)],
        )

    def test_ready_to_publish_task__get_actions__user_can_publish__active_bundle_in_progress(self):
        mark_page_as_ready_to_publish(self.page)
        self.assertEqual(
            self.page.current_workflow_task.get_actions(self.page, self.publishing_admin),
            [("unlock", "Unlock editing", False)],
        )

    def test_ready_to_publish_task__get_actions__user_can_publish__bundle_ready_to_publish(self):
        mark_page_as_ready_to_publish(self.page)

        self.mark_bundle_as_ready_to_publish()

        actions = self.page.current_workflow_task.get_actions(self.page, self.publishing_admin)
        self.assertEqual(actions, [])

    @patch("cms.workflows.wagtail_hooks.update_action_menu")
    def test_workflow_page_action_hook_not_actioned_in_irrelevant_contexts(self, mocked_update):
        # add page
        home_page = HomePage.objects.first()
        self.client.get(
            reverse("wagtailadmin_pages:add", args=("standard_pages", "informationpage", home_page.pk)),
        )
        mocked_update.assert_not_called()

        # edit non-BundledPageMixin model
        self.client.get(reverse("wagtailadmin_pages:edit", args=[home_page.id]))
        mocked_update.assert_not_called()

    def test_action_menu_for_self_approval(self):
        self.client.force_login(self.publishing_admin)
        mark_page_as_ready_for_review(self.page, self.publishing_admin)

        response = self.client.get(self.edit_url)
        menu_items = response.context["action_menu"].menu_items

        self.assertEqual(len(menu_items), 4)
        self.assertActionIn("action-publish", menu_items)
        self.assertActionIn("action-unpublish", menu_items)
        self.assertActionIn("action-cancel-workflow", menu_items)
        self.assertActionIn("reject", menu_items)
        self.assertActionNotIn("approve", menu_items)

    def test_action_menu_locked_item_first_in_list(self):
        self.client.force_login(self.publishing_admin)
        mark_page_as_ready_to_publish(self.page, self.publishing_admin)

        response = self.client.get(self.edit_url)
        action_menu = response.context["action_menu"]
        self.assertIsInstance(action_menu.default_item, PageLockedMenuItem)

    def test_action_menu_fully_locked_when_in_bundle_ready_to_be_published(self):
        self.client.force_login(self.publishing_admin)
        mark_page_as_ready_to_publish(self.page, self.publishing_admin)
        self.mark_bundle_as_ready_to_publish()

        response = self.client.get(self.edit_url)
        action_menu = response.context["action_menu"]
        self.assertIsInstance(action_menu.default_item, PageLockedMenuItem)
        self.assertEqual(action_menu.menu_items, [])

    def test_action_menu_labels__in_review(self):
        self.client.force_login(self.publishing_admin)
        mark_page_as_ready_for_review(self.page, self.publishing_officer)

        response = self.client.get(self.edit_url)
        menu_items = response.context["action_menu"].menu_items
        # unpublish, publish, approve, approve with comment, reject
        self.assertEqual(len(menu_items), 5)

        self.assertActionIn("action-publish", menu_items)
        self.assertActionIn("action-unpublish", menu_items)
        self.assertActionIn("approve", menu_items)
        self.assertActionIn("reject", menu_items)
        self.assertActionNotIn("locked-approve", menu_items)
        self.assertActionNotIn("unlock", menu_items)

        labels = {item.label for item in menu_items}
        self.assertIn("Approve", labels)
        self.assertIn("Approve with comment", labels)

    def test_action_menu_labels__in_ready_to_publish__in_bundle(self):
        self.client.force_login(self.publishing_admin)

        mark_page_as_ready_to_publish(self.page, self.publishing_officer)
        response = self.client.get(self.edit_url)
        menu_items = response.context["action_menu"].menu_items

        self.assertEqual(len(menu_items), 1)  # unlock

        self.assertActionIn("unlock", menu_items)
        self.assertActionNotIn("locked-approve", menu_items)

        labels = {item.label for item in menu_items}
        self.assertIn("Unlock editing", labels)
        self.assertNotIn("Publish", labels)
        self.assertNotIn("Approve and Publish", labels)

    def test_action_menu_labels__in_ready_to_publish__no_bundle(self):
        self.client.force_login(self.publishing_admin)
        page = StatisticalArticlePageFactory()
        mark_page_as_ready_to_publish(page, self.publishing_officer)

        response = self.client.get(reverse("wagtailadmin_pages:edit", args=[page.pk]))
        menu_items = response.context["action_menu"].menu_items

        self.assertEqual(len(menu_items), 2)  # unlock, publish
        self.assertActionIn("unlock", menu_items)
        self.assertActionIn("locked-approve", menu_items)

        labels = {item.label for item in menu_items}
        self.assertIn("Publish", labels)
        self.assertIn("Unlock editing", labels)
        self.assertNotIn("Approve and Publish", labels)


class WorkflowPermissionTweaks(WagtailTestUtils, TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.page = StatisticalArticlePageFactory()

        cls.superuser = cls.create_superuser(username="admin")
        cls.user = UserFactory(access_admin=True)

        cls.publishing_admin = UserFactory()
        cls.publishing_admin.groups.add(Group.objects.get(name=settings.PUBLISHING_ADMINS_GROUP_NAME))
        cls.publishing_officer = UserFactory()
        cls.publishing_officer.groups.add(Group.objects.get(name=settings.PUBLISHING_OFFICERS_GROUP_NAME))

    def test_can_lock__in_review(self):
        mark_page_as_ready_for_review(self.page)

        for user in [self.user, self.superuser]:
            with self.subTest(msg=f"{user=} cannot lock as they must be a PA or PO"):
                tester = BasePagePermissionTester(user=user, page=self.page)
                self.assertFalse(tester.can_lock())

        for user in [self.publishing_officer, self.publishing_admin]:
            with self.subTest(msg=f"{user=} can lock"):
                tester = BasePagePermissionTester(user=user, page=self.page)
                self.assertTrue(tester.can_lock())

    def test_can_lock__ready_to_publish(self):
        mark_page_as_ready_to_publish(self.page)

        for user in [self.user, self.superuser, self.publishing_officer, self.publishing_admin]:
            with self.subTest(msg=f"{user=} can lock"):
                tester = BasePagePermissionTester(user=user, page=self.page)
                self.assertFalse(tester.can_lock())
