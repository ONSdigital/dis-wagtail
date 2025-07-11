from datetime import timedelta
from unittest.mock import patch

from django.core import mail
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from wagtail.test.utils.form_data import inline_formset, nested_form_data

from cms.articles.tests.factories import StatisticalArticlePageFactory
from cms.bundles.api import BundleAPIClientError
from cms.bundles.enums import BundleStatus
from cms.bundles.models import Bundle, BundleDataset, BundleTeam
from cms.bundles.tests.factories import BundleFactory, BundlePageFactory
from cms.datasets.tests.factories import DatasetFactory
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


@override_settings(ONS_BUNDLE_API_ENABLED=True)
class TestBundleAPISignalHandlers(TestCase):
    def setUp(self):
        """Set up the test case."""
        self.patcher = patch("cms.bundles.signal_handlers.BundleAPIClient")
        self.mock_client_class = self.patcher.start()
        self.mock_client = self.mock_client_class.return_value

    def tearDown(self):
        """Clean up after the test."""
        self.patcher.stop()

    def test_bundle_creation_does_not_call_api(self):
        """Test that creating a bundle does not call the Dataset API."""
        bundle = BundleFactory(name="Test Bundle")

        self.mock_client.create_bundle.assert_not_called()

        bundle.refresh_from_db()
        self.assertIsNone(bundle.bundle_api_id)

    def test_bundle_creation_with_pages_and_datasets_does_not_call_api(self):
        """Test that creating a bundle with pages and datasets does not call the API on creation."""
        page = StatisticalArticlePageFactory()
        dataset = DatasetFactory()

        # Create bundle with pages and datasets
        bundle = BundleFactory(name="Test Bundle")
        BundlePageFactory(parent=bundle, page=page)
        BundleDataset.objects.create(parent=bundle, dataset=dataset)

        # Bundle creation should not call the API
        self.mock_client.create_bundle.assert_not_called()

        # But adding datasets should trigger update_bundle if the bundle has bundle_api_id
        # Since this bundle doesn't have bundle_api_id, update_bundle should not be called
        self.mock_client.update_bundle.assert_not_called()

    def test_bundle_status_update_calls_api(self):
        """Test that updating bundle status calls the Dataset API."""
        bundle = BundleFactory(bundle_api_id="api-bundle-123")

        # Clear any calls from bundle creation
        self.mock_client.reset_mock()

        bundle.status = BundleStatus.APPROVED
        bundle.save()

        self.mock_client.update_bundle_status.assert_called_once_with("api-bundle-123", BundleStatus.APPROVED)

    def test_bundle_deletion_calls_api(self):
        """Test that deleting a bundle calls the Dataset API."""
        bundle = BundleFactory(bundle_api_id="api-bundle-123")
        bundle_id = bundle.bundle_api_id

        # Clear any calls from bundle creation
        self.mock_client.reset_mock()

        bundle.delete()

        self.mock_client.delete_bundle.assert_called_once_with(bundle_id)

    def test_bundle_deletion_without_api_id_does_not_call_api(self):
        """Test that deleting a bundle without bundle_api_id doesn't call the API."""
        bundle = BundleFactory(bundle_api_id=None)

        # Clear any calls from bundle creation
        self.mock_client.reset_mock()

        bundle.delete()

        self.mock_client.delete_bundle.assert_not_called()

    def test_adding_dataset_to_bundle_calls_api(self):
        """Test that adding a dataset to a bundle calls the Dataset API."""
        bundle = BundleFactory(bundle_api_id="api-bundle-123")
        dataset = DatasetFactory()

        # Clear any calls from bundle creation
        self.mock_client.reset_mock()

        BundleDataset.objects.create(parent=bundle, dataset=dataset)

        self.mock_client.update_bundle.assert_called_once()
        call_args = self.mock_client.update_bundle.call_args[0]
        self.assertEqual(call_args[0], "api-bundle-123")  # bundle_id
        self.assertEqual(call_args[1]["title"], bundle.name)  # bundle_data

    def test_removing_dataset_from_bundle_calls_api(self):
        """Test that removing a dataset from a bundle calls the Dataset API."""
        bundle = BundleFactory(bundle_api_id="api-bundle-123")
        dataset = DatasetFactory()
        bundle_dataset = BundleDataset.objects.create(parent=bundle, dataset=dataset)

        # Clear any calls from bundle creation
        self.mock_client.reset_mock()

        bundle_dataset.delete()

        self.mock_client.update_bundle.assert_called_once()
        call_args = self.mock_client.update_bundle.call_args[0]
        self.assertEqual(call_args[0], "api-bundle-123")  # bundle_id

    def test_bundle_creation_does_not_call_api_even_with_errors(self):
        """Test that bundle creation doesn't call the API even if there would be errors."""
        self.mock_client.create_bundle.side_effect = BundleAPIClientError("API Error")

        # This should not raise an exception and should not call the API
        bundle = BundleFactory(name="Test Bundle")

        # The bundle should still be saved
        self.assertTrue(bundle.pk)
        self.assertEqual(bundle.name, "Test Bundle")
        self.assertIsNone(bundle.bundle_api_id)

        # API should not be called
        self.mock_client.create_bundle.assert_not_called()

    def test_api_error_during_status_update_does_not_break_save(self):
        """Test that API errors during status update don't prevent saving."""
        bundle = BundleFactory(bundle_api_id="api-bundle-123")

        # Clear any calls from bundle creation
        self.mock_client.reset_mock()
        self.mock_client.update_bundle_status.side_effect = BundleAPIClientError("API Error")

        # This should not raise an exception
        bundle.status = BundleStatus.APPROVED
        bundle.save()

        # The bundle should still be saved with the new status
        bundle.refresh_from_db()
        self.assertEqual(bundle.status, BundleStatus.APPROVED)

    def test_api_error_during_deletion_does_not_break_deletion(self):
        """Test that API errors during deletion don't prevent deletion."""
        bundle = BundleFactory(bundle_api_id="api-bundle-123")
        bundle_pk = bundle.pk

        # Clear any calls from bundle creation
        self.mock_client.reset_mock()
        self.mock_client.delete_bundle.side_effect = BundleAPIClientError("API Error")

        # This should not raise an exception
        bundle.delete()

        # The bundle should still be deleted
        self.assertFalse(Bundle.objects.filter(pk=bundle_pk).exists())


@override_settings(ONS_BUNDLE_API_ENABLED=False)
class TestBundleAPISignalHandlersDisabled(TestCase):
    def setUp(self):
        """Set up the test case."""
        self.patcher = patch("cms.bundles.signal_handlers.BundleAPIClient")
        self.mock_client_class = self.patcher.start()
        self.mock_client = self.mock_client_class.return_value

    def tearDown(self):
        """Clean up after the test."""
        self.patcher.stop()

    def test_bundle_creation_does_not_call_api_when_disabled(self):
        """Test that creating a bundle does not call the API when the flag is off."""
        BundleFactory(name="Test Bundle")
        self.mock_client.create_bundle.assert_not_called()

    def test_bundle_status_update_does_not_call_api_when_disabled(self):
        """Test that updating bundle status does not call the API when disabled."""
        bundle = BundleFactory(bundle_api_id="api-bundle-123")
        self.mock_client.reset_mock()

        bundle.status = BundleStatus.APPROVED
        bundle.save()

        self.mock_client.update_bundle_status.assert_not_called()

    def test_bundle_deletion_does_not_call_api_when_disabled(self):
        """Test that deleting a bundle does not call the API when disabled."""
        bundle = BundleFactory(bundle_api_id="api-bundle-123")
        self.mock_client.reset_mock()

        bundle.delete()

        self.mock_client.delete_bundle.assert_not_called()

    def test_adding_dataset_to_bundle_does_not_call_api_when_disabled(self):
        """Test that adding a dataset to a bundle does not call the API when disabled."""
        bundle = BundleFactory(bundle_api_id="api-bundle-123")
        dataset = DatasetFactory()
        self.mock_client.reset_mock()

        BundleDataset.objects.create(parent=bundle, dataset=dataset)

        self.mock_client.update_bundle.assert_not_called()

    def test_removing_dataset_from_bundle_does_not_call_api_when_disabled(self):
        """Test that removing a dataset from a bundle does not call the API when disabled."""
        bundle = BundleFactory(bundle_api_id="api-bundle-123")
        dataset = DatasetFactory()
        bundle_dataset = BundleDataset.objects.create(parent=bundle, dataset=dataset)
        self.mock_client.reset_mock()

        bundle_dataset.delete()

        self.mock_client.update_bundle.assert_not_called()
