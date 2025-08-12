import json
from datetime import timedelta
from unittest.mock import patch

import responses
from django.core import mail
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from wagtail.test.utils.form_data import inline_formset, nested_form_data

from cms.articles.tests.factories import StatisticalArticlePageFactory
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


@override_settings(DIS_DATASETS_BUNDLE_API_ENABLED=True)
@responses.activate
class TestBundleAPISignalHandlers(TestCase):
    def test_bundle_creation_does_not_call_api(self):
        """Test that creating a bundle does not call the Dataset API."""
        bundle = BundleFactory()

        # No API calls should be made for bundle creation
        self.assertEqual(len(responses.calls), 0)

        bundle.refresh_from_db()
        self.assertIsNone(bundle.bundle_api_content_id)

    def test_bundle_creation_with_pages_and_datasets_does_not_call_api(self):
        """Test that creating a bundle with pages and datasets does not call the API on creation."""
        page = StatisticalArticlePageFactory()
        dataset = DatasetFactory()

        # Create bundle with pages and datasets
        bundle = BundleFactory()
        BundlePageFactory(parent=bundle, page=page)
        BundleDataset.objects.create(parent=bundle, dataset=dataset)

        # Bundle creation should not call the API
        # Since the bundle doesn't have bundle_api_content_id, adding datasets should not call the API either
        self.assertEqual(len(responses.calls), 0)

    def test_bundle_status_update_calls_api(self):
        """Test that updating bundle status calls the Dataset API."""
        bundle = BundleFactory(bundle_api_content_id="api-bundle-123")

        # Mock the API endpoint for bundle state update
        responses.add(
            responses.PUT,
            "https://dummy_base_api/bundles/api-bundle-123/state",
            json={"status": "success", "message": "Bundle state updated"},
            status=200,
        )

        bundle.status = BundleStatus.APPROVED
        bundle.save()

        # Verify the API was called
        self.assertEqual(len(responses.calls), 1)
        self.assertEqual(responses.calls[0].request.url, "https://dummy_base_api/bundles/api-bundle-123/state")

        request_body = json.loads(responses.calls[0].request.body)
        self.assertEqual(request_body["state"], BundleStatus.APPROVED)

    def test_bundle_deletion_calls_api(self):
        """Test that deleting a bundle calls the Dataset API."""
        bundle = BundleFactory(bundle_api_content_id="api-bundle-123")
        bundle_id = bundle.bundle_api_content_id

        # Mock the API endpoint for bundle deletion
        responses.add(
            responses.DELETE,
            "https://dummy_base_api/bundles/api-bundle-123",
            json={"status": "success", "message": "Bundle deleted"},
            status=200,
        )

        bundle.delete()

        # Verify the API was called
        self.assertEqual(len(responses.calls), 1)
        self.assertEqual(responses.calls[0].request.url, f"https://dummy_base_api/bundles/{bundle_id}")

    def test_bundle_deletion_without_api_id_does_not_call_api(self):
        """Test that deleting a bundle without bundle_api_content_id doesn't call the API."""
        bundle = BundleFactory(bundle_api_content_id=None)

        bundle.delete()

        # No API calls should be made
        self.assertEqual(len(responses.calls), 0)

    def test_adding_dataset_to_bundle_calls_api(self):
        """Test that adding a dataset to a bundle calls the Dataset API."""
        bundle = BundleFactory(bundle_api_content_id="api-bundle-123")
        dataset = DatasetFactory()

        # Mock the API response to return a full Bundle object with contents following swagger spec
        mock_response = {
            "id": "api-bundle-123",
            "title": "Test Bundle",
            "bundle_type": "MANUAL",
            "preview_teams": [{"id": "team-uuid-1"}],
            "state": "DRAFT",
            "created_at": "2025-07-14T10:30:00.000Z",
            "created_by": {"email": "test@example.com"},
            "updated_at": "2025-07-14T10:30:00.000Z",
            "contents": [
                {
                    "id": "content-123",
                    "content_type": "DATASET",
                    "metadata": {
                        "dataset_id": dataset.namespace,
                        "edition_id": dataset.edition,
                        "version_id": dataset.version,
                        "title": "Test Dataset Title",
                    },
                    "state": "APPROVED",
                    "links": {
                        "edit": (
                            f"https://publishing.ons.gov.uk/data-admin/edit/datasets/{dataset.namespace}/"
                            f"editions/time-series/versions/{dataset.version}"
                        ),
                        "preview": (
                            f"https://publishing.ons.gov.uk/data-admin/preview/datasets/{dataset.namespace}/"
                            f"editions/time-series/versions/{dataset.version}"
                        ),
                    },
                }
            ],
        }

        # Mock the API endpoint for adding content to bundle
        responses.add(
            responses.POST,
            "https://dummy_base_api/bundles/api-bundle-123/contents",
            json=mock_response,
            status=200,
        )

        bundle_dataset = BundleDataset.objects.create(parent=bundle, dataset=dataset)

        # Verify the API was called
        self.assertEqual(len(responses.calls), 1)
        self.assertEqual(responses.calls[0].request.url, "https://dummy_base_api/bundles/api-bundle-123/contents")

        # Check the request body contains the correct content item
        request_body = json.loads(responses.calls[0].request.body)
        self.assertEqual(request_body["content_type"], "DATASET")
        self.assertEqual(request_body["metadata"]["dataset_id"], dataset.namespace)
        self.assertEqual(request_body["metadata"]["edition_id"], dataset.edition)
        self.assertEqual(request_body["metadata"]["version_id"], dataset.version)

        # Verify that the bundle_api_content_id was extracted and saved
        bundle_dataset.refresh_from_db()
        self.assertEqual(bundle_dataset.bundle_api_content_id, "content-123")

    def test_removing_dataset_from_bundle_calls_api(self):
        """Test that removing a dataset from a bundle calls the Dataset API."""
        bundle = BundleFactory(bundle_api_content_id="api-bundle-123")
        dataset = DatasetFactory()
        bundle_dataset = BundleDataset.objects.create(
            parent=bundle, dataset=dataset, bundle_api_content_id="content-123"
        )

        # Mock the API endpoint for removing content from bundle
        responses.add(
            responses.DELETE,
            "https://dummy_base_api/bundles/api-bundle-123/contents/content-123",
            json={"status": "success", "message": "Content removed from bundle"},
            status=200,
        )

        bundle_dataset.delete()

        # Verify the API was called
        self.assertEqual(len(responses.calls), 1)
        self.assertEqual(
            responses.calls[0].request.url, "https://dummy_base_api/bundles/api-bundle-123/contents/content-123"
        )

    def test_bundle_creation_does_not_call_api_even_with_errors(self):
        """Test that bundle creation doesn't call the API even if there would be errors."""
        # This should not raise an exception and should not call the API
        bundle = BundleFactory()

        # The bundle should still be saved
        self.assertTrue(bundle.pk)
        self.assertIsNone(bundle.bundle_api_content_id)

        # API should not be called
        self.assertEqual(len(responses.calls), 0)

    def test_api_error_during_status_update_does_not_break_save(self):
        """Test that API errors during status update don't prevent saving."""
        bundle = BundleFactory(bundle_api_content_id="api-bundle-123")

        # Mock the API endpoint to return an error
        responses.add(
            responses.PUT,
            "https://dummy_base_api/bundles/api-bundle-123/state",
            json={"error": "API Error"},
            status=500,
        )

        # This should not raise an exception
        bundle.status = BundleStatus.APPROVED
        bundle.save()

        # The bundle should still be saved with the new status
        bundle.refresh_from_db()
        self.assertEqual(bundle.status, BundleStatus.APPROVED)

    def test_api_error_during_deletion_does_not_break_deletion(self):
        """Test that API errors during deletion don't prevent deletion."""
        bundle = BundleFactory(bundle_api_content_id="api-bundle-123")
        bundle_pk = bundle.pk

        # Mock the API endpoint to return an error
        responses.add(
            responses.DELETE,
            "https://dummy_base_api/bundles/api-bundle-123",
            json={"error": "API Error"},
            status=500,
        )

        # This should not raise an exception
        bundle.delete()

        # The bundle should still be deleted
        self.assertFalse(Bundle.objects.filter(pk=bundle_pk).exists())

    def test_adding_dataset_without_content_id_in_response_logs_error(self):
        """Test that if the API response doesn't contain the expected content_id, an error is logged."""
        bundle = BundleFactory(bundle_api_content_id="api-bundle-123")
        dataset = DatasetFactory()

        # Mock the API response to return a Bundle without the expected content following swagger spec
        mock_response = {
            "id": "api-bundle-123",
            "title": "Test Bundle",
            "bundle_type": "MANUAL",
            "preview_teams": [{"id": "team-uuid-1"}],
            "state": "DRAFT",
            "created_at": "2025-07-14T10:30:00.000Z",
            "created_by": {"email": "test@example.com"},
            "updated_at": "2025-07-14T10:30:00.000Z",
            "contents": [],  # Empty contents array
        }

        # Mock the API endpoint for adding content to bundle
        responses.add(
            responses.POST,
            "https://dummy_base_api/bundles/api-bundle-123/contents",
            json=mock_response,
            status=200,
        )

        with self.assertLogs("cms.bundles.signal_handlers", level="ERROR") as cm:
            bundle_dataset = BundleDataset.objects.create(parent=bundle, dataset=dataset)

        self.assertIn("Could not find content_id in response for bundle", cm.output[0])

        # Verify that the bundle_api_content_id was not set
        bundle_dataset.refresh_from_db()
        self.assertIsNone(bundle_dataset.bundle_api_content_id)

    def test_removing_dataset_without_bundle_api_content_id_does_not_call_api(self):
        """Test that removing a dataset without bundle_api_content_id doesn't call the API."""
        bundle = BundleFactory(bundle_api_content_id="api-bundle-123")
        dataset = DatasetFactory()
        bundle_dataset = BundleDataset.objects.create(parent=bundle, dataset=dataset, bundle_api_content_id=None)

        bundle_dataset.delete()

        # No API calls should be made
        self.assertEqual(len(responses.calls), 0)

    def test_adding_dataset_to_bundle_without_bundle_api_content_id_does_not_call_api(self):
        """Test that adding a dataset to a bundle without bundle_api_content_id doesn't call the API."""
        bundle = BundleFactory(bundle_api_content_id=None)
        dataset = DatasetFactory()

        BundleDataset.objects.create(parent=bundle, dataset=dataset)

        # No API calls should be made
        self.assertEqual(len(responses.calls), 0)

    def test_api_error_during_adding_dataset_does_not_break_save(self):
        """Test that API errors during adding dataset don't prevent saving."""
        bundle = BundleFactory(bundle_api_content_id="api-bundle-123")
        dataset = DatasetFactory()

        # Mock the API endpoint to return an error
        responses.add(
            responses.POST,
            "https://dummy_base_api/bundles/api-bundle-123/contents",
            json={"error": "API Error"},
            status=500,
        )

        # This should not raise an exception
        bundle_dataset = BundleDataset.objects.create(parent=bundle, dataset=dataset)

        # The bundle_dataset should still be saved
        self.assertTrue(bundle_dataset.pk)
        self.assertIsNone(bundle_dataset.bundle_api_content_id)

    def test_api_error_during_removing_dataset_does_not_break_deletion(self):
        """Test that API errors during removing dataset don't prevent deletion."""
        bundle = BundleFactory(bundle_api_content_id="api-bundle-123")
        dataset = DatasetFactory()
        bundle_dataset = BundleDataset.objects.create(
            parent=bundle, dataset=dataset, bundle_api_content_id="content-123"
        )
        bundle_dataset_pk = bundle_dataset.pk

        # Mock the API endpoint to return an error
        responses.add(
            responses.DELETE,
            "https://dummy_base_api/bundles/api-bundle-123/contents/content-123",
            json={"error": "API Error"},
            status=500,
        )

        # This should not raise an exception
        bundle_dataset.delete()

        # The bundle_dataset should still be deleted
        self.assertFalse(BundleDataset.objects.filter(pk=bundle_dataset_pk).exists())

    def test_add_team_triggers_preview_teams_sync(self):
        """Test that adding a team to a bundle calls the API to sync preview teams."""
        bundle = BundleFactory(bundle_api_content_id="api-bundle-123")
        team = TeamFactory(identifier="team-identifier-1")

        # Mock the API endpoint for bundle update
        responses.add(
            responses.PUT,
            "https://dummy_base_api/bundles/api-bundle-123",
            json={"status": "success", "message": "Bundle updated"},
            status=200,
        )

        # Add team to bundle via BundleTeam creation - this should trigger the sync
        BundleTeam.objects.create(parent=bundle, team=team)

        # Verify the API was called
        self.assertEqual(len(responses.calls), 1)
        self.assertEqual(responses.calls[0].request.url, "https://dummy_base_api/bundles/api-bundle-123")

        # Check the request body contains the correct preview teams
        request_body = json.loads(responses.calls[0].request.body)
        self.assertEqual(request_body["preview_teams"], [{"id": "team-identifier-1"}])

    def test_remove_team_triggers_preview_teams_sync(self):
        """Test that removing a team from a bundle calls the API to sync preview teams."""
        bundle = BundleFactory(bundle_api_content_id="api-bundle-123")
        team1 = TeamFactory(identifier="team-identifier-1")
        team2 = TeamFactory(identifier="team-identifier-2")

        # Add teams to bundle first
        bundle_team1 = BundleTeam.objects.create(parent=bundle, team=team1)
        BundleTeam.objects.create(parent=bundle, team=team2)

        # Clear responses to focus on the removal
        responses.reset()

        # Mock the API endpoint for bundle update
        responses.add(
            responses.PUT,
            "https://dummy_base_api/bundles/api-bundle-123",
            json={"status": "success", "message": "Bundle updated"},
            status=200,
        )

        # Remove one team - this should trigger the sync
        bundle_team1.delete()

        # Verify the API was called
        self.assertEqual(len(responses.calls), 1)
        self.assertEqual(responses.calls[0].request.url, "https://dummy_base_api/bundles/api-bundle-123")

        # Check the request body contains only the remaining team
        request_body = json.loads(responses.calls[0].request.body)
        self.assertEqual(request_body["preview_teams"], [{"id": "team-identifier-2"}])

    def test_clear_teams_triggers_preview_teams_sync(self):
        """Test that clearing all teams from a bundle calls the API to sync preview teams."""
        bundle = BundleFactory(bundle_api_content_id="api-bundle-123")
        team1 = TeamFactory(identifier="team-identifier-1")
        team2 = TeamFactory(identifier="team-identifier-2")

        # Add teams to bundle first
        bundle_team1 = BundleTeam.objects.create(parent=bundle, team=team1)
        bundle_team2 = BundleTeam.objects.create(parent=bundle, team=team2)

        # Clear responses to focus on the clear operation
        responses.reset()

        # Mock the API endpoint for bundle update - expect 2 calls since we delete each BundleTeam separately
        responses.add(
            responses.PUT,
            "https://dummy_base_api/bundles/api-bundle-123",
            json={"status": "success", "message": "Bundle updated"},
            status=200,
        )
        responses.add(
            responses.PUT,
            "https://dummy_base_api/bundles/api-bundle-123",
            json={"status": "success", "message": "Bundle updated"},
            status=200,
        )

        # Clear all teams by deleting BundleTeam objects - this should trigger the sync
        bundle_team1.delete()
        bundle_team2.delete()

        # Verify the API was called twice (once for each deletion)
        self.assertEqual(len(responses.calls), 2)

        # The last call should show empty preview teams
        request_body = json.loads(responses.calls[-1].request.body)
        self.assertEqual(request_body["preview_teams"], [])

    def test_sync_preview_teams_skips_bundle_without_api_id(self):
        """Test that the sync is skipped if the bundle doesn't have an API ID."""
        bundle = BundleFactory(bundle_api_content_id=None)
        team = TeamFactory(identifier="team-identifier-1")

        # Add team to bundle - this should not trigger any API call
        BundleTeam.objects.create(parent=bundle, team=team)

        # No API calls should be made
        self.assertEqual(len(responses.calls), 0)

    def test_sync_preview_teams_handles_api_errors_gracefully(self):
        """Test that API errors during preview teams sync don't prevent the operation."""
        bundle = BundleFactory(bundle_api_content_id="api-bundle-123")
        team = TeamFactory(identifier="team-identifier-1")

        # Mock the API endpoint to return an error
        responses.add(
            responses.PUT,
            "https://dummy_base_api/bundles/api-bundle-123",
            json={"error": "API Error"},
            status=500,
        )

        # This should not raise an exception, but should log the error
        with self.assertLogs("cms.bundles.signal_handlers", level="ERROR") as cm:
            BundleTeam.objects.create(parent=bundle, team=team)

        # Verify the API was called
        self.assertEqual(len(responses.calls), 1)

        # Verify error was logged
        self.assertIn("Failed to sync preview teams for bundle", cm.output[0])

        # The team should still be added to the bundle
        self.assertTrue(bundle.teams.filter(team=team).exists())


@override_settings(DIS_DATASETS_BUNDLE_API_ENABLED=False)
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
        bundle = BundleFactory(bundle_api_content_id="api-bundle-123")
        self.mock_client.reset_mock()

        bundle.status = BundleStatus.APPROVED
        bundle.save()

        self.mock_client.update_bundle_state.assert_not_called()

    def test_bundle_deletion_does_not_call_api_when_disabled(self):
        """Test that deleting a bundle does not call the API when disabled."""
        bundle = BundleFactory(bundle_api_content_id="api-bundle-123")
        self.mock_client.reset_mock()

        bundle.delete()

        self.mock_client.delete_bundle.assert_not_called()

    def test_adding_dataset_to_bundle_does_not_call_api_when_disabled(self):
        """Test that adding a dataset to a bundle does not call the API when disabled."""
        bundle = BundleFactory(bundle_api_content_id="api-bundle-123")
        dataset = DatasetFactory()
        self.mock_client.reset_mock()

        BundleDataset.objects.create(parent=bundle, dataset=dataset)

        self.mock_client.add_content_to_bundle.assert_not_called()

    def test_removing_dataset_from_bundle_does_not_call_api_when_disabled(self):
        """Test that removing a dataset from a bundle does not call the API when disabled."""
        bundle = BundleFactory(bundle_api_content_id="api-bundle-123")
        dataset = DatasetFactory()
        bundle_dataset = BundleDataset.objects.create(
            parent=bundle, dataset=dataset, bundle_api_content_id="content-123"
        )
        self.mock_client.reset_mock()

        bundle_dataset.delete()

        self.mock_client.delete_content_from_bundle.assert_not_called()

    def test_sync_preview_teams_disabled_when_api_is_disabled(self):
        """Test that preview teams sync is skipped when the API is disabled."""
        bundle = BundleFactory(bundle_api_content_id="api-bundle-123")
        team = TeamFactory(identifier="team-identifier-1")
        self.mock_client.reset_mock()

        # Add team to bundle - this should not trigger any API call
        BundleTeam.objects.create(parent=bundle, team=team)

        # No API calls should be made
        self.mock_client.update_bundle.assert_not_called()
