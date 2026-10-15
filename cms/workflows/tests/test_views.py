from django.test import TestCase
from django.urls import reverse
from wagtail.models import TaskState, WorkflowState
from wagtail.test.utils.wagtail_tests import WagtailTestUtils

from cms.standard_pages.tests.factories import InformationPageFactory
from cms.workflows.models import ReadyToPublishGroupTask
from cms.workflows.tests.utils import mark_page_as_ready_to_publish


class LegacyUnlockWorkflowViewTestCase(WagtailTestUtils, TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.page = InformationPageFactory()

        cls.unlock_url = reverse("workflows:unlock", args=(cls.page.pk,))
        cls.superuser = cls.create_superuser("admin")

    def setUp(self):
        self.client.force_login(self.superuser)

    def test_legacy_unlock_url_with_bad_page_id_redirects(self):
        page_id = 99999
        response = self.client.get(reverse("workflows:unlock", args=(page_id,)))

        self.assertRedirects(
            response,
            reverse("wagtailadmin_pages:edit", args=(page_id,)),
            fetch_redirect_response=False,
        )

    def test_legacy_unlock_get_redirects_without_changing_workflow(self):
        workflow_state = mark_page_as_ready_to_publish(self.page)
        task_id = workflow_state.current_task_state_id

        response = self.client.get(self.unlock_url)

        self.assertRedirects(
            response,
            reverse("wagtailadmin_pages:edit", args=(self.page.pk,)),
            fetch_redirect_response=False,
        )
        workflow_state.refresh_from_db()
        self.assertEqual(workflow_state.current_task_state_id, task_id)
        self.assertEqual(workflow_state.status, WorkflowState.STATUS_IN_PROGRESS)

    def test_legacy_unlock_post_does_not_change_workflow(self):
        # legacy url now just redirects and doesn't affect the workflow state
        workflow_state = mark_page_as_ready_to_publish(self.page)
        task_id = workflow_state.current_task_state_id
        self.assertIsInstance(self.page.current_workflow_task, ReadyToPublishGroupTask)

        response = self.client.post(self.unlock_url)

        self.assertRedirects(
            response,
            reverse("wagtailadmin_pages:edit", args=(self.page.pk,)),
            fetch_redirect_response=False,
        )
        workflow_state.refresh_from_db()
        self.page.refresh_from_db()
        self.assertIsInstance(self.page.current_workflow_task, ReadyToPublishGroupTask)
        self.assertEqual(workflow_state.status, workflow_state.STATUS_IN_PROGRESS)
        self.assertEqual(workflow_state.current_task_state_id, task_id)

    def test_page_editor_reject_returns_ready_page_to_editable_draft(self):
        workflow_state = mark_page_as_ready_to_publish(self.page)
        ready_task_state = workflow_state.current_task_state

        response = self.client.post(
            reverse("wagtailadmin_pages:edit", args=(self.page.pk,)),
            {"action-workflow-action": "true", "workflow-action-name": "reject"},
        )

        self.assertRedirects(
            response, reverse("wagtailadmin_pages:edit", args=(self.page.pk,)), fetch_redirect_response=False
        )
        ready_task_state.refresh_from_db()
        workflow_state.refresh_from_db()
        self.page.refresh_from_db()
        self.assertEqual(ready_task_state.status, TaskState.STATUS_CANCELLED)
        self.assertEqual(workflow_state.status, WorkflowState.STATUS_NEEDS_CHANGES)
        self.assertIsNone(self.page.current_workflow_task)
        self.assertIsNone(self.page.get_lock())
