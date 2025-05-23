from datetime import timedelta

from django.core import mail
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from cms.articles.tests.factories import StatisticalArticlePageFactory
from cms.bundles.enums import BundleStatus
from cms.bundles.models import BundleTeam
from cms.bundles.tests.factories import BundleFactory, BundlePageFactory
from cms.teams.models import Team
from cms.teams.tests.factories import TeamFactory
from cms.users.tests.factories import UserFactory


class TestNotifications(TestCase):
    def setUp(self):
        """Set up the test case."""
        # Clear the mail outbox before each test
        mail.outbox = []

    ### AC 1: Preview team set up
    # Scenario: A bundle is created in preview and with assigned team
    # 1. A bundle is created with status "In Preview"
    # 2. The bundle has a team assigned at creation
    # 3. The team will get a notification

    def test_bundle_in_preview_notification_is_sent_once(self):
        bundle = BundleFactory(in_review=True, name="Preview Bundle")

        preview_team = TeamFactory()
        previewer = UserFactory()
        previewer.teams.set([preview_team])

        another_previewer = UserFactory()
        another_previewer.teams.set([preview_team])

        bt = BundleTeam(parent=bundle, team=preview_team)
        bt.save()

        self.assertEqual(len(mail.outbox), 1)
        self.assertIn(previewer.email, mail.outbox[0].to)
        self.assertIn(another_previewer.email, mail.outbox[0].to)
        self.assertIn(f'Your team "{preview_team.name}" was added to a bundle In review', mail.outbox[0].subject)

    ### AC 2: Assigning teams to existing bundles

    # 2.1 Scenario: Adding a team to a bundle triggers a notification
    # 1. A bundle exits and is in preview
    # 2. A new team is assigned to the bundle
    # 3. The team will get a notification

    def test_bundle_in_preview_gets_a_team_assigned_then_a_notification_is_sent(self):
        """Test that when a bundle exists and is in preview, when a new team is assigned,
        the team will get a notification.
        """
        bundle = BundleFactory(in_review=True, name="Preview Bundle")

        preview_team = Team.objects.create(identifier="foo", name="Preview team")

        previewer = UserFactory()
        previewer.teams.set([preview_team])

        bundle_team = BundleTeam(parent=bundle, team=preview_team)
        bundle_team.save()

        self.assertEqual(len(mail.outbox), 1)
        self.assertIn(previewer.email, mail.outbox[0].to)
        self.assertIn(f'Your team "{preview_team.name}" was added to a bundle In review', mail.outbox[0].subject)

    # 2.2 Scenario: Re-adding a team to a bundle triggers a notification
    # 1. A bundle exits and is in preview
    # 2. The bundle has a team assigned
    # 3. We remove the team
    # 4. We add the team back
    # 5. The team will get a notification
    def test_readding_team_to_bundle_triggers_notification(self):
        bundle = BundleFactory(in_review=True, name="Preview Bundle")

        preview_team = Team.objects.create(identifier="foo", name="Preview team")

        previewer = UserFactory()
        previewer.teams.set([preview_team])

        bundle_team = BundleTeam.objects.create(parent=bundle, team=preview_team)

        self.assertEqual(len(mail.outbox), 1)
        self.assertIn(previewer.email, mail.outbox[0].to)
        self.assertIn(f'Your team "{preview_team.name}" was added to a bundle In review', mail.outbox[0].subject)

        # Now remove and assign the team again, and expect a new email
        mail.outbox = []
        bundle_team.delete()
        self.assertListEqual(bundle.teams.get_object_list(), [])
        bundle_team = BundleTeam.objects.create(parent=bundle, team=preview_team)
        self.assertEqual(len(mail.outbox), 1)

    ### AC 3: Publication is live
    # 1. I create a bundle in preview
    # 2. I publish the bundle
    # 3. An email is sent

    # Four scenarios: management command, manually, release calendar and scheduled

    def skip_test_email_is_sent_when_bundle_is_published_with_management_command(self):
        """Test that when a bundle is published manually (with a management command), an email is sent."""
        bundle = BundleFactory(approved=True, name="Approved Bundle")
        bundle.publication_date = timezone.now() - timedelta(days=1)
        bundle.save()

        preview_team = Team.objects.create(identifier="foo", name="Preview team")

        previewer = UserFactory()
        previewer.teams.set([preview_team])

        # assign the team to the bundle
        BundleTeam.objects.create(parent=bundle, team=preview_team)

        # Clear outbox because creating a bundle in preview sends an email
        mail.outbox = []

        call_command("publish_bundles")

        self.assertEqual(len(mail.outbox), 1)
        self.assertIn(f'Bundle "{bundle.name}" status changed to Published', mail.outbox[0].subject)

    def skip_test_email_is_sent_when_bundle_is_published_via_manual_publication(self):
        """Test that when a bundle is published manually (via the admin), an email is sent."""
        # Create a user and log in
        user = UserFactory(is_staff=True, is_superuser=True)
        self.client.force_login(user)

        # Create a bundle with status "Approved"
        bundle = BundleFactory(status=BundleStatus.APPROVED, name="Approved Bundle")
        bundle.publication_date = timezone.now()
        bundle.save()

        bundle_page = BundlePageFactory(parent=bundle, page=StatisticalArticlePageFactory())

        response = self.client.post(
            reverse("bundle:edit", args=[bundle.pk]),
            {
                "status": "APPROVED",
                "bundled_pages-TOTAL_FORMS": "1",
                "bundled_pages-INITIAL_FORMS": "1",
                "bundled_pages-MIN_NUM_FORMS": "0",
                "bundled_pages-MAX_NUM_FORMS": "1000",
                "bundled_pages-0-page": "14",
                "bundled_pages-0-id": bundle_page.page.pk,
                "bundled_pages-0-ORDER": "1",
                "bundled_pages-0-DELETE": "",
                "teams-TOTAL_FORMS": "1",
                "teams-INITIAL_FORMS": "1",
                "teams-MIN_NUM_FORMS": "0",
                "teams-MAX_NUM_FORMS": "1000",
                "teams-0-team": "1",
                "teams-0-id": "4",
                "teams-0-ORDER": "1",
                "teams-0-DELETE": "",
                "action-publish": "publish",
            },
        )

        self.assertEqual(len(mail.outbox), 1)
        self.assertIn(f'Bundle "{bundle.name}" status changed to Published', mail.outbox[0].subject)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(bundle.status, BundleStatus.PUBLISHED)

    # TODO: Release calendar triggered publication
    def test_email_is_sent_when_bundle_is_published_via_release_calendar(self): ...

    # TODO: Scheduled publication triggered publication
    def test_email_is_sent_when_bundle_is_published_via_bundle_publication_date(self): ...

    ### AC 4: Notification is only sent on the first change to "In Preview"
    def test_notification_sent_only_on_first_change_to_in_preview(self):
        """Test that a notification is sent only on the first change to 'In Preview'."""
        bundle = BundleFactory(name="Draft Bundle")

        preview_team = TeamFactory()
        previewer = UserFactory()
        previewer.teams.set([preview_team])

        bt = BundleTeam(parent=bundle, team=preview_team)
        bt.save()

        # Set the bundle status to "In Preview"
        bundle.status = BundleStatus.IN_REVIEW
        bundle.save()

        # Ensure the notification is sent on the first change to In Preview
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn(previewer.email, mail.outbox[0].to)
        self.assertIn(f'Bundle "{bundle.name}" status changed to In Review', mail.outbox[0].subject)

        # Clear the outbox and change the status back and forth
        mail.outbox = []

        # Change the status to "Draft" and then back to "In Preview"
        bundle.status = BundleStatus.DRAFT
        bundle.save()
        bundle.status = BundleStatus.IN_REVIEW
        bundle.save()

        # Ensure no additional notification is sent
        self.assertEqual(len(mail.outbox), 0)
