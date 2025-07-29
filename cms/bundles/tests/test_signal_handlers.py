from datetime import timedelta
from unittest.mock import patch

from django.core import mail
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from wagtail.models import ModelLogEntry
from wagtail.test.utils import WagtailTestUtils
from wagtail.test.utils.form_data import inline_formset, nested_form_data, rich_text, streamfield

from cms.articles.tests.factories import StatisticalArticlePageFactory
from cms.bundles.enums import BundleStatus
from cms.bundles.models import BundleTeam
from cms.bundles.tests.factories import BundleFactory, BundlePageFactory
from cms.teams.tests.factories import TeamFactory
from cms.users.tests.factories import UserFactory
from cms.workflows.tests.utils import mark_page_as_ready_for_review, mark_page_as_ready_to_publish


class TestNotifications(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.preview_team = TeamFactory()
        cls.previewer = UserFactory()
        cls.previewer.teams.set([cls.preview_team])

    def setUp(self):
        """Set up the test case."""
        # Clear the mail outbox before each test
        mail.outbox = []

    def test_bundle_in_preview_notification_is_sent_once(self):
        """Test that when a bundle is created and is in preview and has a preview team,
        then a notification is sent to the preview team.
        """
        bundle = BundleFactory(in_review=True, name="Preview Bundle")

        another_previewer = UserFactory()
        another_previewer.teams.set([self.preview_team])

        bundle_team = BundleTeam(parent=bundle, team=self.preview_team)
        bundle_team.save()

        self.assertEqual(len(mail.outbox), 1)
        self.assertIn(self.previewer.email, mail.outbox[0].to)
        self.assertIn(another_previewer.email, mail.outbox[0].to)

        self.assertIn(f'Bundle "{bundle.name}" is ready for review', mail.outbox[0].subject)

    def test_bundle_in_preview_gets_a_team_assigned_then_a_notification_is_sent(self):
        """Test that when a bundle exists and is in preview, when a new team is assigned,
        the team will get a notification.
        """
        bundle = BundleFactory(in_review=True, name="Preview Bundle")

        bundle_team = BundleTeam(parent=bundle, team=self.preview_team)
        bundle_team.save()

        self.assertEqual(len(mail.outbox), 1)
        self.assertIn(self.previewer.email, mail.outbox[0].to)
        self.assertIn(f'Bundle "{bundle.name}" is ready for review', mail.outbox[0].subject)
        self.assertIn(bundle.full_inspect_url, mail.outbox[0].body)

    def test_readding_team_to_bundle_triggers_notification(self):
        bundle = BundleFactory(in_review=True, name="Preview Bundle")

        bundle_team = BundleTeam.objects.create(parent=bundle, team=self.preview_team)

        self.assertEqual(len(mail.outbox), 1)
        self.assertIn(self.previewer.email, mail.outbox[0].to)
        self.assertIn(f'Bundle "{bundle.name}" is ready for review', mail.outbox[0].subject)

        # Now remove and assign the team again, and expect a new email
        mail.outbox = []
        bundle_team.delete()
        self.assertListEqual(bundle.teams.get_object_list(), [])
        bundle_team = BundleTeam.objects.create(parent=bundle, team=self.preview_team)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn(bundle.full_inspect_url, mail.outbox[0].body)

    def test_email_is_sent_when_bundle_is_published_with_management_command(self):
        """Test that when a bundle is published manually (with a management command), an email is sent."""
        # NB: Scheduled bundles are published using the management command.

        bundle = BundleFactory(approved=True, name="Approved Bundle")
        bundle.publication_date = timezone.now() - timedelta(days=1)
        bundle.save()

        BundleTeam.objects.create(parent=bundle, team=self.preview_team)

        # Clear outbox because creating a bundle in preview sends an email
        mail.outbox = []

        call_command("publish_bundles")

        bundle.refresh_from_db()
        self.assertEqual(bundle.status, BundleStatus.PUBLISHED)

        self.assertEqual(len(mail.outbox), 1)
        self.assertIn(f'Bundle "{bundle.name}" has been published', mail.outbox[0].subject)

    def test_email_is_sent_when_bundle_is_published_via_manual_publication(self):
        """Test that when a bundle is published manually (via the admin), an email is sent."""
        user = UserFactory(is_staff=True, is_superuser=True)
        self.client.force_login(user)

        page = StatisticalArticlePageFactory()
        page.save_revision()
        bundle = BundleFactory(status=BundleStatus.APPROVED, name="Approved Bundle")
        BundleTeam.objects.create(parent=bundle, team=self.preview_team)
        bundle_page = BundlePageFactory(parent=bundle, page=page)

        response = self.client.post(
            reverse("bundle:edit", args=[bundle.pk]),
            nested_form_data(
                {
                    "name": bundle.name,
                    "status": BundleStatus.PUBLISHED,
                    "bundled_pages": inline_formset([{"page": bundle_page.page_id}]),
                    "bundled_datasets": inline_formset([]),
                    "teams": inline_formset([{"team": self.preview_team.id}]),
                    "action-publish": "publish",
                }
            ),
        )

        self.assertRedirects(response, reverse("bundle:index"))

        bundle.refresh_from_db()
        self.assertEqual(bundle.status, BundleStatus.PUBLISHED)

        self.assertEqual(len(mail.outbox), 1)
        self.assertIn(f'Bundle "{bundle.name}" has been published', mail.outbox[0].subject)

    def test_notification_sent_only_on_first_change_to_in_preview(self):
        """Test that a notification is sent only on the first change to 'In Preview'."""
        bundle = BundleFactory(name="Draft Bundle")

        bundle_team = BundleTeam(parent=bundle, team=self.preview_team)
        bundle_team.save()

        bundle.status = BundleStatus.IN_REVIEW
        bundle.save()

        # Ensure the notification is sent on the first change to In Preview
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn(self.previewer.email, mail.outbox[0].to)
        self.assertIn(f'Bundle "{bundle.name}" is ready for review', mail.outbox[0].subject)
        self.assertIn(bundle.full_inspect_url, mail.outbox[0].body)

        # Clear the outbox and change the status to "Draft" and then back to "In Preview"
        mail.outbox = []
        bundle.status = BundleStatus.DRAFT
        bundle.save()
        bundle.status = BundleStatus.IN_REVIEW
        bundle.save()

        # Ensure no additional notification is sent
        self.assertEqual(len(mail.outbox), 0)


@override_settings(SLACK_NOTIFICATIONS_WEBHOOK_URL="https://slack.example.com")
@patch("cms.bundles.signal_handlers.notify_slack_of_status_change")
class WorkflowSignalsTestCase(WagtailTestUtils, TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.superuser = cls.create_superuser(username="admin")
        cls.bundle = BundleFactory(name="The Bundle", status=BundleStatus.DRAFT)
        cls.statistical_article_page = StatisticalArticlePageFactory()
        BundlePageFactory(parent=cls.bundle, page=cls.statistical_article_page)

        cls.edit_page_url = reverse("wagtailadmin_pages:edit", args=[cls.statistical_article_page.id])

    def get_raw_form_data(self):
        return {
            "title": self.statistical_article_page.title,
            "slug": self.statistical_article_page.slug,
            "summary": rich_text(self.statistical_article_page.summary),
            "main_points_summary": rich_text(self.statistical_article_page.main_points_summary),
            "release_date": self.statistical_article_page.release_date,
            "content": streamfield(
                [("section", {"title": "Test", "content": streamfield([("rich_text", rich_text("text"))])})]
            ),
            "datasets": streamfield([]),
            "dataset_sorting": "AS_SHOWN",
            "corrections": streamfield([]),
            "notices": streamfield([]),
            "headline_figures": streamfield([]),
            "featured_chart": streamfield([]),
        }

    def setUp(self):
        self.client.force_login(self.superuser)

    def test_cancelling_page_workflow_when_ready_to_publish_moves_linked_bundle_to_preview(self, mock_notify):
        mark_page_as_ready_to_publish(self.statistical_article_page, self.superuser)
        self.bundle.status = BundleStatus.APPROVED
        self.bundle.save(update_fields=["status"])

        self.assertFalse(ModelLogEntry.objects.filter(action="bundles.update_status").exists())

        data = self.get_raw_form_data()
        data["action-cancel-workflow"] = "Cancel workflow"

        self.client.post(self.edit_page_url, nested_form_data(data), follow=True)

        self.bundle.refresh_from_db()
        self.assertEqual(self.bundle.status, BundleStatus.IN_REVIEW)

        self.assertTrue(mock_notify.called)

        self.assertTrue(ModelLogEntry.objects.filter(action="bundles.update_status").exists())

    def test_cancelling_page_workflow_when_in_preview_doesnt_change_linked_bundle_status(self, mock_notify):
        self.assertFalse(ModelLogEntry.objects.filter(action="bundles.update_status").exists())

        mark_page_as_ready_for_review(self.statistical_article_page, self.superuser)

        data = self.get_raw_form_data()
        data["action-cancel-workflow"] = "Cancel workflow"

        self.client.post(self.edit_page_url, nested_form_data(data), follow=True)

        self.bundle.refresh_from_db()
        self.assertEqual(self.bundle.status, BundleStatus.DRAFT)

        self.assertFalse(mock_notify.called)
        self.assertFalse(ModelLogEntry.objects.filter(action="bundles.update_status").exists())
