import datetime
from unittest.mock import patch

from django.conf import settings
from django.contrib.auth.models import Group
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from wagtail.admin.action_menu import PageLockedMenuItem
from wagtail.models import Revision
from wagtail.test.utils.form_data import nested_form_data, rich_text, streamfield
from wagtail.test.utils.timestamps import submittable_timestamp
from wagtail.test.utils.wagtail_tests import WagtailTestUtils
from wagtail.utils.timestamps import render_timestamp

from cms.articles.tests.factories import StatisticalArticlePageFactory
from cms.bundles.enums import BundleStatus
from cms.bundles.tests.factories import BundleFactory, BundlePageFactory
from cms.core.permission_testers import BasePagePermissionTester
from cms.core.tests.factories import BasePageFactory
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


class WorkflowTweaksBaseTestCase(WagtailTestUtils, TestCase):
    """Shared helpers for workflow tweak tests."""

    @classmethod
    def setUpTestData(cls):
        cls.publishing_admin = UserFactory()
        cls.publishing_admin.groups.add(Group.objects.get(name=settings.PUBLISHING_ADMINS_GROUP_NAME))
        cls.publishing_officer = UserFactory()
        cls.publishing_officer.groups.add(Group.objects.get(name=settings.PUBLISHING_OFFICERS_GROUP_NAME))

    def assertActionIn(self, action, menu_items):  # pylint: disable=invalid-name
        actions = {item.name for item in menu_items}
        self.assertIn(action, actions)

    def assertActionNotIn(self, action, menu_items):  # pylint: disable=invalid-name
        actions = {item.name for item in menu_items}
        self.assertNotIn(action, actions)


class WorkflowTweaksTestCase(WorkflowTweaksBaseTestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.page = StatisticalArticlePageFactory()
        cls.edit_url = reverse("wagtailadmin_pages:edit", args=[cls.page.id])

        cls.bundle = BundleFactory()
        cls.bundle_page = BundlePageFactory(parent=cls.bundle, page=cls.page)

    def mark_bundle_as_ready_to_publish(self):
        # mark the bundle as ready to publish
        self.bundle.status = BundleStatus.APPROVED
        self.bundle.save(update_fields=["status"])

    def get_simple_post_data(self, page):
        return nested_form_data(
            {
                "title": page.title,
                "slug": page.slug,
                "summary": rich_text(page.summary),
                "main_points_summary": rich_text(page.main_points_summary),
                "release_date": page.release_date,
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

    def test_amend_page_action_menu_items_hook__not_in_bundle(self):
        # un-bundle
        self.bundle.bundled_pages.all().delete()

        # Mark the page as ready for review
        workflow_state = mark_page_as_ready_for_review(self.page, self.publishing_admin)

        # Log in as publishing_admin (who was the last editor)
        self.client.force_login(self.publishing_admin)
        response = self.client.get(self.edit_url)

        self.assertNotContains(response, 'data-workflow-action-name="locked-approve"')
        self.assertNotContains(response, 'data-workflow-action-name="approve"')
        self.assertNotContains(response, "Approve")
        self.assertNotContains(response, "Approve with comment")

        # Log in as the second user (who was not the last editor)
        self.client.force_login(self.publishing_officer)
        response = self.client.get(self.edit_url)

        self.assertNotContains(response, 'data-workflow-action-name="locked-approve"')
        self.assertContains(response, 'data-workflow-action-name="approve"')
        self.assertContains(response, "Approve")
        self.assertContains(response, "Approve with comment")

        # Now mark as ready to publish. Both PA and PO should be able to publish
        progress_page_workflow(workflow_state, self.publishing_officer)

        response = self.client.get(self.edit_url)
        self.assertContains(response, 'data-workflow-action-name="locked-approve"')
        self.assertContains(response, "Publish")
        self.assertContains(response, "Unlock editing")

        # .. and check as PA too
        self.client.force_login(self.publishing_admin)
        response = self.client.get(self.edit_url)
        self.assertContains(response, 'data-workflow-action-name="locked-approve"')
        self.assertContains(response, "Publish")
        self.assertContains(response, "Unlock editing")

    def test_amend_page_action_menu_items_hook__in_bundle(self):
        # Mark the page as ready for review
        workflow_state = mark_page_as_ready_for_review(self.page, self.publishing_admin)

        # Log in as publishing_admin (who was the last editor)
        self.client.force_login(self.publishing_admin)
        response = self.client.get(self.edit_url)

        self.assertNotContains(response, 'data-workflow-action-name="locked-approve"')
        self.assertNotContains(response, 'data-workflow-action-name="approve"')
        self.assertNotContains(response, "Approve")
        self.assertNotContains(response, "Approve with comment")

        # Log in as the second user (who was not the last editor)
        self.client.force_login(self.publishing_officer)
        response = self.client.get(self.edit_url)

        self.assertNotContains(response, 'data-workflow-action-name="locked-approve"')
        self.assertContains(response, 'data-workflow-action-name="approve"')
        self.assertContains(response, "Approve")
        self.assertContains(response, "Approve with comment")

        # Now mark as ready to publish. The page should be locked
        progress_page_workflow(workflow_state, self.publishing_officer)

        response = self.client.get(self.edit_url)
        self.assertNotContains(response, 'data-workflow-action-name="locked-approve"')
        self.assertNotContains(response, 'data-workflow-action-name="approve"')
        self.assertContains(response, "Unlock editing")

        # .. and check as PA too
        self.client.force_login(self.publishing_admin)
        response = self.client.get(self.edit_url)
        self.assertNotContains(response, 'data-workflow-action-name="locked-approve"')
        self.assertNotContains(response, 'data-workflow-action-name="approve"')
        self.assertContains(response, "Unlock editing")

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

        data = self.get_simple_post_data(self.page)
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

    def test_before_edit_page__prevents_schedule_mechanism_when_in_bundle(self):
        """Test that users cannot set individual page publishing schedule while in a bundle."""
        self.client.force_login(self.publishing_admin)

        self.assertIsNone(self.page.go_live_at)

        go_live_at = timezone.now() + datetime.timedelta(weeks=3)
        data = self.get_simple_post_data(self.page)
        data["go_live_at"] = submittable_timestamp(go_live_at)
        del data["action-workflow-action"]
        del data["workflow-action-name"]
        response = self.client.post(self.edit_url, data, follow=True)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Cannot set page-level schedule while the page is in a bundle.")

        self.assertIsNone(response.context["page"].go_live_at)
        self.assertFalse(
            Revision.objects.for_instance(self.page)
            .filter(content__go_live_at__startswith=str(go_live_at.date()))
            .exists()
        )

    def test_before_edit_page__prevents_expiry_schedule_mechanism_when_in_bundle(self):
        """Test that users cannot set individual page publishing schedule while in a bundle."""
        self.client.force_login(self.publishing_admin)

        self.assertIsNone(self.page.expire_at)

        expire_at = timezone.now() + datetime.timedelta(weeks=3)
        data = self.get_simple_post_data(self.page)
        data["expire_at"] = submittable_timestamp(expire_at)
        del data["action-workflow-action"]
        del data["workflow-action-name"]
        response = self.client.post(self.edit_url, data, follow=True)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Cannot set page-level schedule while the page is in a bundle.")

        self.assertIsNone(response.context["page"].expire_at)
        self.assertFalse(
            Revision.objects.for_instance(self.page)
            .filter(content__go_live_at__startswith=str(expire_at.date()))
            .exists()
        )

    def test_before_edit_page__doesnt_prevent_scheduling_when_not_in_bundle(self):
        # un-bundle
        self.bundle.bundled_pages.all().delete()
        self.client.force_login(self.publishing_admin)

        go_live_at = timezone.now() + datetime.timedelta(weeks=3)
        self.assertFalse(
            Revision.objects.for_instance(self.page)
            .filter(content__go_live_at__startswith=str(go_live_at.date()))
            .exists()
        )

        data = self.get_simple_post_data(self.page)
        data["go_live_at"] = submittable_timestamp(go_live_at)
        del data["action-workflow-action"]
        del data["workflow-action-name"]

        response = self.client.post(self.edit_url, data, follow=True)

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Cannot set page-level schedule while the page is in a bundle.")

        # Check that revision with go_live_at in its content JSON exists
        self.assertTrue(
            Revision.objects.for_instance(self.page)
            .filter(content__go_live_at__startswith=str(go_live_at.date()))
            .exists()
        )

        self.assertContains(response, render_timestamp(go_live_at))
        self.assertEqual(response.context["page"].go_live_at.date(), go_live_at.date())

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

        self.assertEqual(len(menu_items), 3)
        self.assertActionIn("action-unpublish", menu_items)
        self.assertActionIn("action-cancel-workflow", menu_items)
        self.assertActionIn("reject", menu_items)
        self.assertActionNotIn("action-publish", menu_items)
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
        # unpublish, approve, approve with comment, reject
        self.assertEqual(len(menu_items), 4)

        self.assertActionIn("approve", menu_items)
        self.assertActionIn("reject", menu_items)
        self.assertActionIn("action-unpublish", menu_items)
        self.assertActionNotIn("action-publish", menu_items)
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

    def test_locked_approve_action__publishes_page(self):
        self.client.force_login(self.publishing_admin)

        draft_page = StatisticalArticlePageFactory(live=False)
        mark_page_as_ready_to_publish(draft_page, self.publishing_officer)

        self.assertFalse(draft_page.live)

        data = self.get_simple_post_data(draft_page)
        data["workflow-action-name"] = "locked-approve"
        response = self.client.post(reverse("wagtailadmin_pages:edit", args=[draft_page.pk]), data, follow=True)

        draft_page.refresh_from_db()
        self.assertContains(response, f"Page &#x27;{draft_page.get_admin_display_title()}&#x27; has been published.")
        self.assertTrue(draft_page.live)

    def test_locked_approve_action__schedules_page(self):
        self.client.force_login(self.publishing_admin)

        draft_page = StatisticalArticlePageFactory(live=False, go_live_at=timezone.now() + datetime.timedelta(days=10))
        mark_page_as_ready_to_publish(draft_page, self.publishing_officer)

        self.assertFalse(draft_page.live)

        data = self.get_simple_post_data(draft_page)
        data["workflow-action-name"] = "locked-approve"
        data["go_live_at"] = draft_page.go_live_at
        response = self.client.post(reverse("wagtailadmin_pages:edit", args=[draft_page.pk]), data, follow=True)

        self.assertFalse(draft_page.live)
        self.assertContains(
            response, f"Page &#x27;{draft_page.get_admin_display_title()}&#x27; has been scheduled for publishing."
        )

    def test_locked_approve_action__publishes_page_with_go_live_in_the_past(self):
        self.client.force_login(self.publishing_admin)

        draft_page = StatisticalArticlePageFactory(live=False, go_live_at=timezone.now() - datetime.timedelta(hours=1))
        mark_page_as_ready_to_publish(draft_page, self.publishing_officer)

        self.assertFalse(draft_page.live)

        data = self.get_simple_post_data(draft_page)
        data["workflow-action-name"] = "locked-approve"
        data["go_live_at"] = draft_page.go_live_at
        response = self.client.post(reverse("wagtailadmin_pages:edit", args=[draft_page.pk]), data, follow=True)

        self.assertFalse(draft_page.live)
        self.assertContains(response, f"Page &#x27;{draft_page.get_admin_display_title()}&#x27; has been published.")

    def test_submit_with_workflow_action_after_workflow_cancelled_raises_validation_error(self):
        # TODO: remove when https://github.com/wagtail/wagtail/issues/13856 is fixed

        self.client.force_login(self.publishing_admin)

        data = self.get_simple_post_data(self.page)
        data["workflow-action-name"] = "approve"
        response = self.client.post(self.edit_url, data, follow=True)

        self.assertContains(response, "Could not perform the action as the page is no longer in a workflow.")


class WorkflowTweaksNonBundledPageTestCase(WorkflowTweaksBaseTestCase):
    """Tests for workflow hook behaviour on pages without BundledPageMixin.

    Ensures that after removing the BundledPageMixin guard from
    amend_page_action_menu_items, pages like ArticleSeriesPage (pre-mixin)
    still enforce self-approval prevention, correct menu items, and allow
    page-level scheduling.
    """

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.page = BasePageFactory()
        cls.edit_url = reverse("wagtailadmin_pages:edit", args=[cls.page.id])

    def get_simple_post_data(self, page):
        return nested_form_data(
            {
                "title": page.title,
                "slug": page.slug,
                "action-workflow-action": "true",
                "workflow-action-name": "approve",
            }
        )

    def test_submitter_cannot_self_approve__action_menu(self):
        """The submitter should not see the approve action in the menu."""
        self.client.force_login(self.publishing_admin)
        mark_page_as_ready_for_review(self.page, self.publishing_admin)

        response = self.client.get(self.edit_url)
        menu_items = response.context["action_menu"].menu_items

        self.assertActionNotIn("approve", menu_items)
        self.assertActionNotIn("locked-approve", menu_items)

    def test_submitter_cannot_self_approve__post(self):
        """POST with approve action by the submitter is blocked with an error message."""
        self.client.force_login(self.publishing_admin)
        mark_page_as_ready_for_review(self.page, self.publishing_admin)
        latest_revision = self.page.latest_revision

        data = self.get_simple_post_data(self.page)
        response = self.client.post(self.edit_url, data, follow=True)

        self.assertContains(
            response, "Cannot self-approve your changes. Please ask another Publishing team member to do so."
        )
        self.page.refresh_from_db()
        self.assertEqual(self.page.latest_revision.pk, latest_revision.pk)

    def test_non_submitter_sees_approve_action(self):
        """A different publishing team member can see and use the approve action."""
        mark_page_as_ready_for_review(self.page, self.publishing_admin)

        self.client.force_login(self.publishing_officer)
        response = self.client.get(self.edit_url)
        menu_items = response.context["action_menu"].menu_items

        self.assertActionIn("approve", menu_items)
        labels = {item.label for item in menu_items}
        self.assertIn("Approve", labels)
        self.assertIn("Approve with comment", labels)

    def test_cancel_workflow_available_in_review(self):
        """Cancel workflow action is present during the review stage."""
        self.client.force_login(self.publishing_admin)
        mark_page_as_ready_for_review(self.page, self.publishing_admin)

        response = self.client.get(self.edit_url)
        self.assertContains(response, 'name="action-cancel-workflow"')

    def test_ready_to_publish__publish_and_unlock_actions_present(self):
        """When ready to publish with no bundle, both Publish and Unlock editing are shown."""
        self.client.force_login(self.publishing_admin)
        mark_page_as_ready_to_publish(self.page, self.publishing_officer)

        response = self.client.get(self.edit_url)
        menu_items = response.context["action_menu"].menu_items

        self.assertEqual(len(menu_items), 2)  # unlock + locked-approve
        self.assertActionIn("locked-approve", menu_items)
        self.assertActionIn("unlock", menu_items)

        labels = {item.label for item in menu_items}
        self.assertIn("Publish", labels)
        self.assertIn("Unlock editing", labels)

    def test_page_level_go_live_scheduling_allowed(self):
        """Page-level go_live_at scheduling is not blocked for non-bundled pages."""
        self.client.force_login(self.publishing_admin)

        go_live_at = timezone.now() + datetime.timedelta(weeks=3)
        data = self.get_simple_post_data(self.page)
        data["go_live_at"] = submittable_timestamp(go_live_at)
        del data["action-workflow-action"]
        del data["workflow-action-name"]

        response = self.client.post(self.edit_url, data, follow=True)

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Cannot set page-level schedule while the page is in a bundle.")
        self.assertTrue(
            Revision.objects.for_instance(self.page)
            .filter(content__go_live_at__startswith=str(go_live_at.date()))
            .exists()
        )

    def test_page_level_expire_at_scheduling_allowed(self):
        """Page-level expire_at scheduling is not blocked for non-bundled pages."""
        self.client.force_login(self.publishing_admin)

        expire_at = timezone.now() + datetime.timedelta(weeks=3)
        data = self.get_simple_post_data(self.page)
        data["expire_at"] = submittable_timestamp(expire_at)
        del data["action-workflow-action"]
        del data["workflow-action-name"]

        response = self.client.post(self.edit_url, data, follow=True)

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Cannot set page-level schedule while the page is in a bundle.")
        self.assertTrue(
            Revision.objects.for_instance(self.page)
            .filter(content__expire_at__startswith=str(expire_at.date()))
            .exists()
        )


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

        tester = BasePagePermissionTester(user=self.user, page=self.page)
        self.assertFalse(tester.can_lock())

        for user in [self.publishing_officer, self.publishing_admin, self.superuser]:
            with self.subTest(msg=f"{user=} can lock"):
                tester = BasePagePermissionTester(user=user, page=self.page)
                self.assertTrue(tester.can_lock())

    def test_can_lock__ready_to_publish(self):
        mark_page_as_ready_to_publish(self.page)

        for user in [self.user, self.superuser, self.publishing_officer, self.publishing_admin]:
            with self.subTest(msg=f"{user=} can lock"):
                tester = BasePagePermissionTester(user=user, page=self.page)
                self.assertFalse(tester.can_lock())
