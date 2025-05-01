from django.test import TestCase
from wagtail.models import Workflow, WorkflowTask

from cms.standard_pages.tests.factories import InformationPageFactory
from cms.workflows.models import GroupReviewTask, ReadyToPublishGroupTask
from cms.workflows.tests.utils import (
    mark_page_as_ready_for_review,
    mark_page_as_ready_to_publish,
)
from cms.workflows.utils import is_page_ready_to_preview, is_page_ready_to_publish


class UtilsTestCase(TestCase):
    def setUp(self):
        # Create a real page using the factory
        self.page = InformationPageFactory(title="Test Information Page")

    def test_workflow_setup(self):
        """Ensure the "Release review" workflow exists with the expected tasks."""
        workflow = Workflow.objects.get(name="Release review")

        # Get the tasks from the workflow
        group_review_task = GroupReviewTask.objects.first()
        ready_to_publish_task = ReadyToPublishGroupTask.objects.first()

        # Make sure the tasks are in the workflow
        self.assertTrue(WorkflowTask.objects.filter(workflow=workflow, task=group_review_task).exists())
        self.assertTrue(WorkflowTask.objects.filter(workflow=workflow, task=ready_to_publish_task).exists())

    def test_is_page_ready_to_preview__without_workflow(self):
        # Page has no workflow state by default
        self.assertFalse(is_page_ready_to_preview(self.page))

    def test_is_page_ready_to_preview__when_marked_as_ready_for_review(self):
        # Start the workflow to put the page in the group review task
        mark_page_as_ready_for_review(self.page)
        self.assertTrue(is_page_ready_to_preview(self.page))

    def test_is_page_ready_to_preview__when_marked_as_ready_to_publish(self):
        # Mark the page as ready to publish to put it in the ready to publish task
        mark_page_as_ready_to_publish(self.page)
        self.assertTrue(is_page_ready_to_preview(self.page))

    def test_is_page_ready_to_publish__without_workflow(self):
        self.assertFalse(is_page_ready_to_publish(self.page))

    def test_is_page_ready_to_publish__with_other_task(self):
        # Start the workflow to put the page in the group review task
        mark_page_as_ready_for_review(self.page)
        self.assertFalse(is_page_ready_to_publish(self.page))

    def test_is_page_ready_to_publish__with_ready_to_publish_task(self):
        # Mark the page as ready to publish to put it in the ready to publish task
        mark_page_as_ready_to_publish(self.page)
        self.assertTrue(is_page_ready_to_publish(self.page))
