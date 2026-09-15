from datetime import timedelta
from http import HTTPStatus
from unittest.mock import patch

from django.core import mail
from django.core.management import call_command
from django.db import transaction
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from wagtail.test.utils import WagtailTestUtils
from wagtail.test.utils.form_data import inline_formset, nested_form_data

from cms.articles.tests.factories import StatisticalArticlePageFactory
from cms.bundles.enums import BundleStatus
from cms.bundles.models import BundleTeam
from cms.bundles.tests.factories import BundleFactory, BundlePageFactory
from cms.bundles.viewsets.bundle import BundleEditView
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
        with self.captureOnCommitCallbacks(execute=True):
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
        with self.captureOnCommitCallbacks(execute=True):
            bundle_team.save()

        self.assertEqual(len(mail.outbox), 1)
        self.assertIn(self.previewer.email, mail.outbox[0].to)
        self.assertIn(f'Bundle "{bundle.name}" is ready for review', mail.outbox[0].subject)
        self.assertIn(bundle.full_inspect_url, mail.outbox[0].body)

    def test_readding_team_to_bundle_triggers_notification(self):
        bundle = BundleFactory(in_review=True, name="Preview Bundle")

        with self.captureOnCommitCallbacks(execute=True):
            bundle_team = BundleTeam.objects.create(parent=bundle, team=self.preview_team)

        self.assertEqual(len(mail.outbox), 1)
        self.assertIn(self.previewer.email, mail.outbox[0].to)
        self.assertIn(f'Bundle "{bundle.name}" is ready for review', mail.outbox[0].subject)

        # Now remove and assign the team again, and expect a new email
        mail.outbox = []
        bundle_team.delete()
        self.assertListEqual(bundle.teams.get_object_list(), [])
        with self.captureOnCommitCallbacks(execute=True):
            BundleTeam.objects.create(parent=bundle, team=self.preview_team)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn(bundle.full_inspect_url, mail.outbox[0].body)

    def test_email_is_sent_when_bundle_is_published_with_management_command(self):
        """Test that when a bundle is published manually (with a management command), an email is sent."""
        # NB: Scheduled bundles are published using the management command.

        bundle = BundleFactory(approved=True, name="Approved Bundle")
        page = StatisticalArticlePageFactory()
        page.save_revision()
        BundlePageFactory(parent=bundle, page=page)
        bundle.publication_date = timezone.now() - timedelta(days=1)
        bundle.save()

        BundleTeam.objects.create(parent=bundle, team=self.preview_team)

        # Clear outbox because creating a bundle in preview sends an email
        mail.outbox = []

        with self.captureOnCommitCallbacks(execute=True):
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

        with self.captureOnCommitCallbacks(execute=True):
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

        with self.captureOnCommitCallbacks(execute=True):
            bundle.status = BundleStatus.IN_REVIEW
            bundle.save()

        # Ensure the notification is sent on the first change to In Preview
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn(self.previewer.email, mail.outbox[0].to)
        self.assertIn(f'Bundle "{bundle.name}" is ready for review', mail.outbox[0].subject)
        self.assertIn(bundle.full_inspect_url, mail.outbox[0].body)

        # Clear the outbox and change the status to "Draft" and then back to "In Preview"
        mail.outbox = []
        with self.captureOnCommitCallbacks(execute=True):
            bundle.status = BundleStatus.DRAFT
            bundle.save()
            bundle.status = BundleStatus.IN_REVIEW
            bundle.save()

        # Ensure no additional notification is sent
        self.assertEqual(len(mail.outbox), 0)


class TestNotificationsNotSentWhenCommitIsRolledBack(WagtailTestUtils, TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.superuser = cls.create_superuser(username="admin")

        cls.preview_team = TeamFactory()
        cls.previewer = UserFactory()
        cls.previewer.teams.set([cls.preview_team])

        cls.another_team = TeamFactory()
        cls.another_previewer = UserFactory()
        cls.another_previewer.teams.set([cls.another_team])

    def setUp(self):
        mail.outbox = []
        self.client.force_login(self.superuser)

        self.bundle = BundleFactory(name="Rollback Bundle")
        self.bundle_team = BundleTeam.objects.create(parent=self.bundle, team=self.preview_team)
        self.edit_url = reverse("bundle:edit", args=[self.bundle.pk])

    @staticmethod
    def fail_after_save():
        save_instance = BundleEditView.save_instance

        def save_instance_then_fail(view):
            save_instance(view)
            raise RuntimeError("Simulated error after bundle was saved")

        return patch.object(BundleEditView, "save_instance", save_instance_then_fail)

    def move_bundle_to_in_review(self):
        with self.captureOnCommitCallbacks():
            self.bundle.status = BundleStatus.IN_REVIEW
            self.bundle.save(update_fields=["status"])

    def get_form_data(self, action, *, new_teams=()):
        teams = [{"id": self.bundle_team.id, "team": self.preview_team.id, "ORDER": "1"}]
        teams += [{"team": team.id} for team in new_teams]

        return nested_form_data(
            {
                "name": self.bundle.name,
                "bundled_pages": inline_formset([]),
                "bundled_datasets": inline_formset([]),
                "teams": inline_formset(teams, initial=1),
                action: action,
            }
        )

    def test_in_review_email_is_not_sent_if_transaction_rolls_back(self):
        with self.fail_after_save(), self.captureOnCommitCallbacks(execute=True) as callbacks:
            response = self.client.post(self.edit_url, self.get_form_data("action-save-to-preview"))

        self.assertEqual(response.status_code, HTTPStatus.OK)

        self.bundle.refresh_from_db()
        self.assertEqual(self.bundle.status, BundleStatus.DRAFT)

        self.assertEqual(callbacks, [])
        self.assertEqual(len(mail.outbox), 0)

        self.bundle_team.refresh_from_db()
        self.assertFalse(self.bundle_team.preview_notification_sent)

    def test_in_review_email_is_not_sent_for_a_newly_assigned_team_when_the_save_is_rolled_back(self):
        """Assigning a team to a bundle already in preview would normally notify,
        so test this does not occur if the transaction rolls back.
        """
        self.move_bundle_to_in_review()

        with self.fail_after_save(), self.captureOnCommitCallbacks(execute=True) as callbacks:
            response = self.client.post(self.edit_url, self.get_form_data("action-edit", new_teams=[self.another_team]))

        self.assertEqual(response.status_code, HTTPStatus.OK)

        self.assertFalse(BundleTeam.objects.filter(parent=self.bundle, team=self.another_team).exists())
        self.assertEqual(callbacks, [])
        self.assertEqual(len(mail.outbox), 0)

    def test_published_email_is_not_sent_when_the_publish_save_is_rolled_back(self):
        self.bundle.status = BundleStatus.APPROVED
        self.bundle.save(update_fields=["status"])

        with (
            self.captureOnCommitCallbacks(execute=True) as callbacks,
            self.assertRaises(RuntimeError),
            transaction.atomic(),
        ):
            self.bundle.status = BundleStatus.PUBLISHED
            self.bundle.save(update_fields=["status"])
            raise RuntimeError("Simulated failure after bundle marked as published")

        self.assertEqual(callbacks, [])
        self.assertEqual(len(mail.outbox), 0)

        self.bundle.refresh_from_db()
        self.assertEqual(self.bundle.status, BundleStatus.APPROVED)

    def test_no_email_sent_when_assigning_the_team_rolls_back(self):
        self.move_bundle_to_in_review()

        with (
            self.captureOnCommitCallbacks(execute=True) as callbacks,
            self.assertRaises(RuntimeError),
            transaction.atomic(),
        ):
            BundleTeam.objects.create(parent=self.bundle, team=self.another_team)
            raise RuntimeError("Simulated failure after assigning team to bundle")

        self.assertEqual(callbacks, [])
        self.assertEqual(len(mail.outbox), 0)
        self.assertFalse(BundleTeam.objects.filter(parent=self.bundle, team=self.another_team).exists())

    def test_in_review_email_is_sent_when_the_save_commits(self):
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(self.edit_url, self.get_form_data("action-save-to-preview"))

        self.assertEqual(response.status_code, HTTPStatus.FOUND)

        self.bundle.refresh_from_db()
        self.assertEqual(self.bundle.status, BundleStatus.IN_REVIEW)

        self.bundle_team.refresh_from_db()
        self.assertTrue(self.bundle_team.preview_notification_sent)

        self.assertEqual(len(mail.outbox), 1)
        self.assertIn(self.previewer.email, mail.outbox[0].to)

    def test_retrying_a_rolled_back_save_sends_the_email_once(self):
        data = self.get_form_data("action-save-to-preview")

        with self.fail_after_save(), self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(self.edit_url, data)

        self.assertEqual(len(mail.outbox), 0)

        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(self.edit_url, data)

        self.assertEqual(response.status_code, HTTPStatus.FOUND)

        self.bundle.refresh_from_db()
        self.assertEqual(self.bundle.status, BundleStatus.IN_REVIEW)

        self.assertEqual(len(mail.outbox), 1)
