from django.conf import settings
from django.contrib.auth.models import Group
from django.test import TestCase, override_settings
from django.urls import reverse
from wagtail.test.utils.form_data import nested_form_data, rich_text, streamfield
from wagtail.test.utils.wagtail_tests import WagtailTestUtils

from cms.articles.tests.factories import StatisticalArticlePageFactory
from cms.bundles.enums import BundleStatus
from cms.bundles.tests.factories import BundlePageFactory
from cms.standard_pages.tests.factories import InformationPageFactory
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


class WorkflowPublishingTestCase(WagtailTestUtils, TestCase):
    """Tests that pages can be published through the approval workflow."""

    @classmethod
    def setUpTestData(cls):
        cls.first_user = UserFactory()
        cls.first_user.groups.add(Group.objects.get(name=settings.PUBLISHING_ADMINS_GROUP_NAME))
        cls.second_user = UserFactory()
        cls.second_user.groups.add(Group.objects.get(name=settings.PUBLISHING_OFFICERS_GROUP_NAME))

    def test_page_published_after_workflow_approval(self):
        """Test that a page is published when the workflow is completed via final approval."""
        # Create a draft page (not live)
        page = InformationPageFactory(live=False)

        # Page should not be live initially
        self.assertFalse(page.live)

        # First user submits for review
        workflow_state = mark_page_as_ready_for_review(page, self.first_user)

        # Page should still not be live after first submission
        page.refresh_from_db()
        self.assertFalse(page.live)

        # First task approval (review/preview stage)
        progress_page_workflow(workflow_state)

        # Page should still not be live after first approval
        page.refresh_from_db()
        self.assertFalse(page.live)
        self.assertTrue(is_page_ready_to_publish(page))

        # Final approval publishes the page
        workflow_state.refresh_from_db()
        workflow_state.current_task_state.approve()

        # Page should now be live
        page.refresh_from_db()
        self.assertTrue(page.live)

    def test_publish_button_not_shown_in_page_edit_view(self):
        """Test that the Publish button is not shown when WAGTAIL_WORKFLOW_REQUIRE_APPROVAL_TO_PUBLISH is True."""
        # Create a draft page (not live) so publish would normally be available
        page = InformationPageFactory(live=False)
        edit_url = reverse("wagtailadmin_pages:edit", args=[page.id])

        self.client.force_login(self.first_user)
        response = self.client.get(edit_url)

        # The publish action should not be present (due to can_publish returning False)
        self.assertNotContains(response, 'name="action-publish"')

    @override_settings(WAGTAIL_WORKFLOW_REQUIRE_APPROVAL_TO_PUBLISH=False)
    def test_publish_button_shown_when_setting_disabled(self):
        """Test that the Publish button is shown when WAGTAIL_WORKFLOW_REQUIRE_APPROVAL_TO_PUBLISH is False."""
        # Create a draft page (not live)
        page = InformationPageFactory(live=False)
        edit_url = reverse("wagtailadmin_pages:edit", args=[page.id])

        self.client.force_login(self.first_user)
        response = self.client.get(edit_url)

        # The publish action should be present when the setting is disabled
        self.assertContains(response, 'name="action-publish"')
