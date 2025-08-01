from django.conf import settings
from django.contrib.auth.models import Group
from django.test import TestCase
from django.urls import reverse
from wagtail.test.utils.form_data import nested_form_data, rich_text, streamfield
from wagtail.test.utils.wagtail_tests import WagtailTestUtils

from cms.articles.tests.factories import StatisticalArticlePageFactory
from cms.bundles.enums import BundleStatus
from cms.bundles.tests.factories import BundlePageFactory
from cms.users.tests.factories import UserFactory
from cms.workflows.tests.utils import (
    mark_page_as_ready_for_review,
    progress_page_workflow,
)
from cms.workflows.utils import is_page_ready_to_publish


class WorkflowTweaksTestCase(WagtailTestUtils, TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.first_user = UserFactory()
        cls.first_user.groups.add(Group.objects.get(name=settings.PUBLISHING_ADMINS_GROUP_NAME))
        cls.second_user = UserFactory()
        cls.second_user.groups.add(Group.objects.get(name=settings.PUBLISHING_OFFICERS_GROUP_NAME))

        cls.page = StatisticalArticlePageFactory()
        cls.edit_url = reverse("wagtailadmin_pages:edit", args=[cls.page.id])

    def test_amend_page_action_menu_items_hook(self):
        # Mark the page as ready for review
        mark_page_as_ready_for_review(self.page, self.first_user)

        # Log in as first_user (who was the last editor)
        self.client.force_login(self.first_user)
        response = self.client.get(self.edit_url)

        self.assertNotContains(response, 'data-workflow-action-name="approve"')
        self.assertNotContains(response, "Approve")
        self.assertNotContains(response, "Approve with comment")

        # Log in as the second user (who was not the last editor)
        self.client.force_login(self.second_user)
        response = self.client.get(self.edit_url)

        self.assertContains(response, 'data-workflow-action-name="approve"')
        self.assertContains(response, "Approve")
        self.assertContains(response, "Approve with comment")

    def test_cancel_workflow_action_menu_item(self):
        # Log in as first_user (who was the last editor)
        self.client.force_login(self.first_user)

        # Mark the page as ready for review
        workflow_state = mark_page_as_ready_for_review(self.page, self.first_user)

        response = self.client.get(self.edit_url)
        self.assertContains(response, 'name="action-cancel-workflow"')

        # ready to publish, but not in a bundle
        progress_page_workflow(workflow_state)
        response = self.client.get(self.edit_url)
        self.assertContains(response, 'name="action-cancel-workflow"')

        # add to bundle, ready to publish
        BundlePageFactory(parent__status=BundleStatus.APPROVED, page=self.page)

        response = self.client.get(self.edit_url)
        self.assertNotContains(response, 'name="action-cancel-workflow"')

    def test_before_edit_page(self):
        """Test that users cannot self-approve their changes."""
        # Log in as first_user
        self.client.force_login(self.first_user)

        mark_page_as_ready_for_review(self.page, self.first_user)
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

        # Now test with second_user
        self.client.force_login(self.second_user)

        response = self.client.post(self.edit_url, data, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Cannot self-approve your changes")

        self.assertTrue(is_page_ready_to_publish(self.page))
        self.page.refresh_from_db()
        self.assertEqual(self.page.latest_revision.user_id, self.second_user.id)
        self.assertNotEqual(self.page.latest_revision.pk, latest_revision.pk)
