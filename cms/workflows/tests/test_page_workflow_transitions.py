import json

from django.urls import reverse
from wagtail.models import PageLogEntry, TaskState, WorkflowState
from wagtail.test.utils.form_data import nested_form_data, rich_text, streamfield

from cms.bundles.enums import BundleStatus
from cms.bundles.tests.factories import BundleFactory, BundlePageFactory
from cms.standard_pages.tests.factories import InformationPageFactory
from cms.users.tests.factories import UserFactory
from cms.workflows.models import GroupReviewTask, ReadyToPublishGroupTask
from cms.workflows.tests.test_workflow_tweaks import WorkflowTweaksBaseTestCase
from cms.workflows.tests.utils import mark_page_as_ready_for_review


class PageWorkflowTransitionTests(WorkflowTweaksBaseTestCase):
    """End-to-end tests for page publishing workflow states and permissions."""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.outsider = UserFactory(username="outsider", access_admin=True)
        cls.page = InformationPageFactory(live=False, title="Draft page")
        cls.edit_url = reverse("wagtailadmin_pages:edit", args=[cls.page.pk])

    def approve_review(self, workflow_state, comment=""):
        task_state = workflow_state.current_task_state
        task_state.task.specific.on_action(task_state, self.publishing_admin, "approve", comment=comment)
        workflow_state.refresh_from_db()
        return task_state

    def post_action(self, user, action, comment=None):
        self.client.force_login(user)
        data = {"action-workflow-action": "true", "workflow-action-name": action}
        if comment is not None:
            data["workflow-action-extra-data"] = json.dumps({"comment": comment})
        return self.client.post(self.edit_url, data, follow=True)

    def editor_data(self, title, action):
        return nested_form_data(
            {
                "title": title,
                "slug": self.page.slug,
                "summary": rich_text("Updated summary"),
                "content": streamfield(
                    [
                        (
                            "section",
                            {"title": "Test section", "content": streamfield([("rich_text", rich_text("text"))])},
                        )
                    ]
                ),
                "topics-TOTAL_FORMS": "0",
                "topics-INITIAL_FORMS": "0",
                "topics-MIN_NUM_FORMS": "0",
                "topics-MAX_NUM_FORMS": "1000",
                action: "true",
            }
        )

    def test_draft_can_be_saved(self):
        self.client.force_login(self.publishing_officer)
        self.assertIsNone(self.page.get_lock())
        response = self.client.post(self.edit_url, self.editor_data("Updated draft", "action-save-draft"), follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context["form"].errors, response.context["form"].errors)
        for formset in response.context["form"].formsets.values():
            self.assertFalse(formset.non_form_errors())
        self.page.refresh_from_db()
        self.assertEqual(self.page.get_latest_revision_as_object().title, "Updated draft")
        self.assertIsNone(self.page.current_workflow_task)

    def test_manually_locked_draft_cannot_be_submitted_by_lock_owner(self):
        self.page.locked = True
        self.page.locked_by = self.publishing_officer
        self.page.save(update_fields=["locked", "locked_by"])
        self.client.force_login(self.publishing_officer)
        self.assertFalse(self.page.get_lock().for_user(self.publishing_officer))
        response = self.client.get(self.edit_url)
        self.assertItemWithPropertyNotIn("name", "action-submit", response.context["action_menu"].menu_items)

        response = self.client.post(self.edit_url, self.editor_data("Submitted draft", "action-submit"), follow=True)

        self.assertContains(response, "Unlock this page before changing its workflow state.")
        self.page.refresh_from_db()
        self.assertIsNone(self.page.current_workflow_state)

    def test_manual_lock_hides_review_actions_and_blocks_direct_posts(self):
        workflow = mark_page_as_ready_for_review(self.page, self.publishing_officer)
        revision_id = self.page.latest_revision_id
        self.page.locked = True
        self.page.locked_by = self.publishing_admin
        self.page.save(update_fields=["locked", "locked_by"])
        self.client.force_login(self.publishing_admin)
        self.assertTrue(self.page.get_lock().for_user(self.publishing_admin))
        self.assertTrue(self.page.permissions_for_user(self.publishing_admin).can_unlock())

        response = self.client.get(self.edit_url)
        self.assertTrue(response.context["action_menu"].context["locked_for_user"])
        self.assertNotContains(response, "Unlock editing")
        menu_items = response.context["action_menu"].menu_items
        for action in ("approve", "reject", "action-cancel-workflow"):
            self.assertItemWithPropertyNotIn("name", action, menu_items)
        self.assertNotContains(response, 'data-workflow-action-name="reject"')

        for action in ("approve", "reject"):
            with self.subTest(action=action):
                response = self.post_action(self.publishing_admin, action)
                self.assertContains(response, "Unlock this page before changing its workflow state.")
                workflow.refresh_from_db()
                self.assertEqual(workflow.current_task_state.status, TaskState.STATUS_IN_PROGRESS)

        response = self.client.post(
            self.edit_url, self.editor_data("Unexpected edit", "action-save-draft"), follow=True
        )
        self.assertContains(response, "Unlock this page before changing its workflow state.")
        self.page.refresh_from_db()
        self.assertEqual(self.page.latest_revision_id, revision_id)

    def test_manual_lock_hides_ready_actions_and_blocks_publish(self):
        workflow = mark_page_as_ready_for_review(self.page, self.publishing_officer)
        self.approve_review(workflow)
        self.page.locked = True
        self.page.locked_by = self.publishing_admin
        self.page.save(update_fields=["locked", "locked_by"])
        self.client.force_login(self.publishing_admin)
        self.assertTrue(self.page.get_lock().for_user(self.publishing_admin))
        self.assertTrue(self.page.permissions_for_user(self.publishing_admin).can_unlock())

        response = self.client.get(self.edit_url)
        menu_items = response.context["action_menu"].menu_items
        for action in ("locked-approve", "reject"):
            self.assertItemWithPropertyNotIn("name", action, menu_items)

        for action in ("locked-approve", "reject"):
            with self.subTest(action=action):
                response = self.post_action(self.publishing_admin, action)
                self.assertContains(response, "Unlock this page before changing its workflow state.")
                workflow.refresh_from_db()
                self.assertEqual(workflow.current_task_state.status, TaskState.STATUS_IN_PROGRESS)
                self.page.refresh_from_db()
                self.assertFalse(self.page.live)

    def test_editor_submission_enters_review_and_locks_page(self):
        self.client.force_login(self.publishing_officer)
        response = self.client.post(self.edit_url, self.editor_data("Submitted draft", "action-submit"), follow=True)
        self.assertEqual(response.status_code, 200)
        self.page.refresh_from_db()
        workflow = self.page.current_workflow_state
        self.assertEqual(workflow.status, WorkflowState.STATUS_IN_PROGRESS)
        self.assertEqual(workflow.current_task_state.status, TaskState.STATUS_IN_PROGRESS)
        self.assertIsInstance(self.page.current_workflow_task, GroupReviewTask)
        for user in (self.publishing_officer, self.publishing_admin):
            with self.subTest(user=user):
                self.assertTrue(self.page.get_lock().for_user(user))
        self.assertEqual(self.page.get_latest_revision_as_object().title, "Submitted draft")

    def test_initial_action_uses_review_workflow_label(self):
        self.client.force_login(self.publishing_officer)
        self.assertContains(self.client.get(self.edit_url), "Submit to Review")

    def test_review_task_has_configured_name(self):
        mark_page_as_ready_for_review(self.page, self.publishing_officer)
        self.assertEqual(self.page.current_workflow_task.name, "In Preview")

    def test_submitter_can_reject_but_cannot_approve(self):
        workflow = mark_page_as_ready_for_review(self.page, self.publishing_officer)
        allowed = {
            name for name, _, _ in self.page.current_workflow_task.get_actions(self.page, user=self.publishing_officer)
        }
        self.assertIn("reject", allowed)
        self.assertNotIn("approve", allowed)
        task_id = workflow.current_task_state_id
        self.post_action(self.publishing_officer, "approve")
        workflow.refresh_from_db()
        self.assertEqual(workflow.current_task_state_id, task_id)
        self.assertEqual(workflow.current_task_state.status, TaskState.STATUS_IN_PROGRESS)

    def test_reviewer_can_approve_or_return_and_outsider_cannot(self):
        workflow = mark_page_as_ready_for_review(self.page, self.publishing_officer)
        actions = self.page.current_workflow_task.get_actions(self.page, user=self.publishing_admin)
        self.assertEqual(
            [label for name, label, _ in actions if name == "approve"], ["Approve", "Approve with comment"]
        )
        self.assertIn("reject", {name for name, _, _ in actions})
        for action in ("approve", "reject"):
            with self.subTest(action=action):
                self.post_action(self.outsider, action)
                workflow.refresh_from_db()
                self.assertEqual(workflow.status, WorkflowState.STATUS_IN_PROGRESS)
                self.assertEqual(workflow.current_task_state.status, TaskState.STATUS_IN_PROGRESS)

    def test_approval_advances_to_ready_and_keeps_lock(self):
        workflow = mark_page_as_ready_for_review(self.page, self.publishing_officer)
        review = self.approve_review(workflow)
        review.refresh_from_db()
        self.assertEqual(review.status, TaskState.STATUS_APPROVED)
        self.assertEqual(workflow.current_task_state.status, TaskState.STATUS_IN_PROGRESS)
        self.assertIsInstance(self.page.current_workflow_task, ReadyToPublishGroupTask)
        for user in (self.publishing_officer, self.publishing_admin):
            self.assertTrue(self.page.get_lock().for_user(user))

    def test_reviewer_can_return_review_page_to_draft(self):
        workflow = mark_page_as_ready_for_review(self.page, self.publishing_officer)
        self.post_action(self.publishing_admin, "reject")
        workflow.refresh_from_db()
        review = workflow.current_task_state
        self.page.refresh_from_db()
        self.assertEqual(review.status, TaskState.STATUS_REJECTED)
        self.assertEqual(review.finished_by_id, self.publishing_admin.pk)
        self.assertEqual(workflow.status, WorkflowState.STATUS_NEEDS_CHANGES)
        self.assertIsNone(self.page.get_lock())

    def test_approval_comment_recorded_in_audit_history(self):
        workflow = mark_page_as_ready_for_review(self.page, self.publishing_officer)
        self.post_action(self.publishing_admin, "approve", comment="Please check figures")
        workflow.refresh_from_db()
        review = workflow.task_states.order_by("started_at").first()
        self.assertEqual(review.comment, "Please check figures")
        self.assertTrue(
            PageLogEntry.objects.filter(
                action="wagtail.workflow.approve", page_id=self.page.pk, data__comment="Please check figures"
            ).exists()
        )
        self.assertIsInstance(workflow.current_task_state.task.specific, ReadyToPublishGroupTask)

    def test_submitter_returns_review_to_editable_draft_and_can_resubmit(self):
        workflow = mark_page_as_ready_for_review(self.page, self.publishing_officer)
        self.post_action(self.publishing_officer, "reject")
        workflow.refresh_from_db()
        review = workflow.current_task_state
        self.page.refresh_from_db()
        self.assertEqual(review.status, TaskState.STATUS_REJECTED)
        self.assertEqual(workflow.status, WorkflowState.STATUS_NEEDS_CHANGES)
        self.assertIsNone(self.page.current_workflow_task)
        self.assertIsNone(self.page.get_lock())
        saved = self.client.post(
            self.edit_url, self.editor_data("Edited after review return", "action-save-draft"), follow=True
        )
        self.assertEqual(saved.status_code, 200)
        self.page.refresh_from_db()
        self.assertEqual(self.page.get_latest_revision_as_object().title, "Edited after review return")
        workflow.resume(user=self.publishing_officer)
        self.assertIsInstance(self.page.current_workflow_task, GroupReviewTask)

    def test_review_return_opens_action_modal_without_changing_state(self):
        workflow = mark_page_as_ready_for_review(self.page, self.publishing_officer)
        self.client.force_login(self.publishing_officer)
        url = reverse(
            "wagtailadmin_pages:collect_workflow_action_data",
            args=[self.page.pk, "reject", workflow.current_task_state_id],
        )
        response = self.client.get(url)
        modal = response.json()
        self.assertEqual(modal["step"], "action")
        self.assertIn("Unlock editing", modal["html"])
        self.assertIn('name="comment"', modal["html"])
        workflow.refresh_from_db()
        self.assertEqual(workflow.status, WorkflowState.STATUS_IN_PROGRESS)

    def test_ready_actions_depend_on_bundle_membership(self):
        workflow = mark_page_as_ready_for_review(self.page, self.publishing_officer)
        self.approve_review(workflow)
        self.assertEqual(
            {name for name, _, _ in self.page.current_workflow_task.get_actions(self.page, user=self.publishing_admin)},
            {"reject", "locked-approve"},
        )
        bundle = BundleFactory()
        BundlePageFactory(parent=bundle, page=self.page)
        # Make a new page object in case the page still has active_bundle=None (cached)
        bundled_page = type(self.page).objects.get(pk=self.page.pk)
        self.assertEqual(
            {
                name
                for name, _, _ in bundled_page.current_workflow_task.get_actions(bundled_page, self.publishing_admin)
            },
            {"reject"},
        )

    def test_publishing_unbundled_page_completes_workflow(self):
        workflow = mark_page_as_ready_for_review(self.page, self.publishing_officer)
        self.approve_review(workflow)
        self.post_action(self.publishing_admin, "locked-approve")
        self.page.refresh_from_db()
        workflow.refresh_from_db()
        self.assertTrue(self.page.live)
        self.assertEqual(self.page.status_string, "live")
        self.assertEqual(workflow.status, WorkflowState.STATUS_APPROVED)

    def test_forged_publish_of_bundled_page_is_rejected(self):
        bundle = BundleFactory()
        BundlePageFactory(parent=bundle, page=self.page)
        workflow = mark_page_as_ready_for_review(self.page, self.publishing_officer)
        self.approve_review(workflow)
        self.post_action(self.publishing_admin, "locked-approve")
        workflow.refresh_from_db()
        self.page.refresh_from_db()
        self.assertFalse(self.page.live)
        self.assertEqual(workflow.status, WorkflowState.STATUS_IN_PROGRESS)

    def test_approved_bundle_hides_return_and_blocks_forged_post(self):
        bundle = BundleFactory()
        BundlePageFactory(parent=bundle, page=self.page)
        workflow = mark_page_as_ready_for_review(self.page, self.publishing_officer)
        self.approve_review(workflow)
        bundle.status = BundleStatus.APPROVED
        bundle.save(update_fields=["status"])
        self.page.refresh_from_db()
        self.assertEqual(self.page.current_workflow_task.get_actions(self.page, user=self.publishing_admin), [])
        response = self.post_action(self.publishing_admin, "reject")
        self.assertContains(response, "You cannot perform this workflow action.")
        workflow.refresh_from_db()
        self.assertEqual(workflow.status, WorkflowState.STATUS_IN_PROGRESS)
        self.assertContains(self.client.get(self.edit_url), "revert the bundle")

    def test_return_from_ready_requires_review_on_resubmission(self):
        workflow = mark_page_as_ready_for_review(self.page, self.publishing_officer)
        self.approve_review(workflow)
        ready = workflow.current_task_state
        self.post_action(self.publishing_admin, "reject")
        ready.refresh_from_db()
        workflow.refresh_from_db()
        self.page.refresh_from_db()
        self.assertEqual(ready.status, TaskState.STATUS_CANCELLED)
        self.assertEqual(workflow.status, WorkflowState.STATUS_NEEDS_CHANGES)
        self.assertIsNone(self.page.get_lock())
        saved = self.client.post(
            self.edit_url, self.editor_data("Edited after ready return", "action-save-draft"), follow=True
        )
        self.assertEqual(saved.status_code, 200)
        self.page.refresh_from_db()
        self.assertEqual(self.page.get_latest_revision_as_object().title, "Edited after ready return")
        workflow.resume(user=self.publishing_officer)
        self.assertIsInstance(self.page.current_workflow_task, GroupReviewTask)

    def test_ready_return_opens_action_modal_without_changing_state(self):
        workflow = mark_page_as_ready_for_review(self.page, self.publishing_officer)
        self.approve_review(workflow)
        self.client.force_login(self.publishing_admin)
        url = reverse(
            "wagtailadmin_pages:collect_workflow_action_data",
            args=[self.page.pk, "reject", workflow.current_task_state_id],
        )
        response = self.client.get(url)
        modal = response.json()
        self.assertEqual(modal["step"], "action")
        self.assertIn("Unlock editing", modal["html"])
        self.assertIn('name="comment"', modal["html"])
        workflow.refresh_from_db()
        self.assertEqual(workflow.status, WorkflowState.STATUS_IN_PROGRESS)
