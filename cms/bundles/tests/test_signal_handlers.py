from datetime import timedelta
from unittest.mock import patch

from django.core import mail
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from wagtail.test.utils.form_data import inline_formset, nested_form_data

from cms.articles.tests.factories import StatisticalArticlePageFactory
from cms.bundles.enums import BundleStatus
from cms.bundles.models import BundleTeam
from cms.bundles.tests.factories import BundleFactory, BundlePageFactory
from cms.teams.tests.factories import TeamFactory
from cms.users.tests.factories import UserFactory


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

        bundle = BundleFactory(status=BundleStatus.APPROVED, name="Approved Bundle")
        BundleTeam.objects.create(parent=bundle, team=self.preview_team)
        bundle_page = BundlePageFactory(parent=bundle, page=StatisticalArticlePageFactory())

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

    def test_that_an_error_is_logged_when_preview_team_member_has_no_email(self):
        """Test that an error is logged when a preview notification email is sent to a preview team
        and one of the members doesn't have an email.
        """
        bundle = BundleFactory(in_review=True, name="Preview Bundle")
        team = TeamFactory()
        user_without_email = UserFactory(email="")
        team.users.add(user_without_email)

        with self.assertLogs("cms.bundles.notifications.email", level="ERROR") as log:
            bundle_team = BundleTeam(parent=bundle, team=team)
            bundle_team.save()

        self.assertEqual(log.records[0].user_id, user_without_email.id)
        self.assertEqual(log.records[0].team_name, team.name)
        self.assertEqual(log.records[0].bundle_name, bundle.name)
        self.assertEqual(log.records[0].email_subject, f'Bundle "{bundle.name}" is ready for review')

        self.assertEqual(len(mail.outbox), 0)

    def test_that_an_error_is_logged_when_send_mail_raises_exception(self):
        """Test that an error is logged when send_mail raises an exception."""
        bundle = BundleFactory(in_review=True, name="Preview Bundle")
        another_previewer = UserFactory()
        another_previewer.teams.set([self.preview_team])

        with (
            patch("cms.bundles.notifications.email.send_mail", side_effect=Exception("SMTP error")),
            self.assertLogs("cms.bundles.notifications.email", level="ERROR") as log,
        ):
            bundle_team = BundleTeam(parent=bundle, team=self.preview_team)
            bundle_team.save()

        record = log.records[0]
        self.assertEqual(record.msg, "Failed to send bundle notification email")
        self.assertEqual(record.team_name, self.preview_team.name)
        self.assertEqual(record.bundle_name, bundle.name)
        self.assertEqual(record.email_subject, f'Bundle "{bundle.name}" is ready for review')
        self.assertEqual(record.recipients, [self.previewer.email, another_previewer.email])
        self.assertEqual(record.error_message, "SMTP error")

        self.assertEqual(len(mail.outbox), 0)
