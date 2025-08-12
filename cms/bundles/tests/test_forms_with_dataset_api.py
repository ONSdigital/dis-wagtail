from unittest.mock import patch

from django.core.exceptions import ValidationError
from django.test import TestCase, override_settings
from wagtail.admin.panels import get_edit_handler
from wagtail.test.utils.form_data import inline_formset, nested_form_data

from cms.bundles.clients.api import BundleAPIClientError
from cms.bundles.enums import BundleStatus
from cms.bundles.models import Bundle, BundleDataset
from cms.bundles.tests.factories import BundleFactory
from cms.datasets.tests.factories import DatasetFactory
from cms.teams.tests.factories import TeamFactory
from cms.users.tests.factories import UserFactory


@override_settings(DIS_DATASETS_BUNDLE_API_ENABLED=True)
class BundleFormSaveWithDatasetAPITestCase(TestCase):
    """Test cases for the BundleAdminForm save method."""

    @classmethod
    def setUpTestData(cls):
        cls.form_class = get_edit_handler(Bundle).get_form_class()
        cls.approver = UserFactory()

    def setUp(self):
        self.patcher = patch("cms.bundles.forms.BundleAPIClient")
        self.mock_client_class = self.patcher.start()
        self.mock_client = self.mock_client_class.return_value

    def tearDown(self):
        self.patcher.stop()

    def test_save_new_bundle_without_datasets_does_not_call_api(self):
        """Test that saving a new bundle without datasets doesn't call the API."""
        self.mock_client.create_bundle.return_value = {"id": "api-bundle-123"}

        raw_data = {
            "name": "Test Bundle",
            "status": BundleStatus.DRAFT,
            "bundled_pages": inline_formset([]),
            "bundled_datasets": inline_formset([]),
            "teams": inline_formset([]),
        }

        form = self.form_class(data=nested_form_data(raw_data), for_user=self.approver)

        self.assertTrue(form.is_valid())
        bundle = form.save()

        # API should not be called for bundles without datasets
        self.mock_client.create_bundle.assert_not_called()
        self.assertIsNone(bundle.bundle_api_content_id)

    def test_save_new_bundle_with_datasets_calls_api(self):
        """Test that saving a new bundle with datasets calls the API."""
        self.mock_client.create_bundle.return_value = {"id": "api-bundle-123"}

        dataset = DatasetFactory(id=123, title="Test Dataset")
        raw_data = {
            "name": "Test Bundle",
            "status": BundleStatus.DRAFT,
            "bundled_pages": inline_formset([]),
            "bundled_datasets": inline_formset([{"dataset": dataset.id}]),
            "teams": inline_formset([]),
        }

        form = self.form_class(data=nested_form_data(raw_data), for_user=self.approver)

        self.assertTrue(form.is_valid())
        bundle = form.save()

        # API should be called for bundles with datasets
        self.mock_client.create_bundle.assert_called_once()
        call_args = self.mock_client.create_bundle.call_args[0][0]
        self.assertEqual(call_args["title"], "Test Bundle")
        self.assertEqual(call_args["bundle_type"], "MANUAL")
        self.assertEqual(call_args["state"], "DRAFT")
        self.assertEqual(call_args["managed_by"], "WAGTAIL")

        # Content should be added separately
        self.mock_client.add_content_to_bundle.assert_called_once()
        content_call_args = self.mock_client.add_content_to_bundle.call_args[0]
        self.assertEqual(content_call_args[0], "api-bundle-123")  # bundle_id
        content_item = content_call_args[1]
        self.assertEqual(content_item["content_type"], "DATASET")
        self.assertEqual(content_item["metadata"]["dataset_id"], dataset.namespace)

        # Bundle should have the API ID set
        self.assertEqual(bundle.bundle_api_content_id, "api-bundle-123")

    def test_save_existing_bundle_uses_standard_behavior(self):
        """Test that saving an existing bundle uses standard Django form behavior."""
        existing_bundle = BundleFactory(name="Existing Bundle")

        raw_data = {
            "name": "Updated Bundle",
            "status": BundleStatus.DRAFT,
            "bundled_pages": inline_formset([]),
            "bundled_datasets": inline_formset([]),
            "teams": inline_formset([]),
        }

        form = self.form_class(instance=existing_bundle, data=nested_form_data(raw_data), for_user=self.approver)

        self.assertTrue(form.is_valid())
        bundle = form.save()

        # API should not be called for existing bundles in form save
        self.mock_client.create_bundle.assert_not_called()
        self.assertEqual(bundle.name, "Updated Bundle")

    def test_save_new_bundle_with_datasets_api_error_raises_validation_error(self):
        """Test that API errors during bundle creation don't prevent saving."""
        self.mock_client.create_bundle.side_effect = BundleAPIClientError("API Error")

        dataset = DatasetFactory(id=123, title="Test Dataset")
        raw_data = {
            "name": "Test Bundle",
            "status": BundleStatus.DRAFT,
            "bundled_pages": inline_formset([]),
            "bundled_datasets": inline_formset([{"dataset": dataset.id}]),
            "teams": inline_formset([]),
        }

        form = self.form_class(data=nested_form_data(raw_data), for_user=self.approver)

        self.assertTrue(form.is_valid())
        with self.assertRaises(ValidationError) as context:
            form.save()
        self.assertEqual(context.exception.message, "Could not communicate with the Dataset API")

    def test_save_new_bundle_with_datasets_no_api_id_returned(self):
        """Test handling when API doesn't return an ID."""
        self.mock_client.create_bundle.return_value = {"message": "Created but no ID"}

        dataset = DatasetFactory(id=123, title="Test Dataset")
        raw_data = {
            "name": "Test Bundle",
            "status": BundleStatus.DRAFT,
            "bundled_pages": inline_formset([]),
            "bundled_datasets": inline_formset([{"dataset": dataset.id}]),
            "teams": inline_formset([]),
        }

        form = self.form_class(data=nested_form_data(raw_data), for_user=self.approver)

        self.assertTrue(form.is_valid())
        with self.assertRaises(ValidationError) as context:
            form.save()

        self.assertEqual(context.exception.message, "Could not communicate with the Dataset API")

        # API should be called
        self.mock_client.create_bundle.assert_called_once()

    def test_save_existing_bundle_with_first_dataset_calls_api(self):
        """Test that editing an existing bundle to add its first dataset calls the API."""
        self.mock_client.create_bundle.return_value = {"id": "api-bundle-456"}

        # Create an existing bundle without datasets
        existing_bundle = BundleFactory(name="Existing Bundle", bundle_api_content_id=None)
        dataset = DatasetFactory(id=123, title="Test Dataset")

        raw_data = {
            "name": "Updated Bundle",
            "status": BundleStatus.DRAFT,
            "bundled_pages": inline_formset([]),
            "bundled_datasets": inline_formset([{"dataset": dataset.id}]),
            "teams": inline_formset([]),
        }

        form = self.form_class(instance=existing_bundle, data=nested_form_data(raw_data), for_user=self.approver)

        self.assertTrue(form.is_valid())
        bundle = form.save()

        # API should be called when adding first dataset to existing bundle
        self.mock_client.create_bundle.assert_called_once()
        call_args = self.mock_client.create_bundle.call_args[0][0]
        self.assertEqual(call_args["title"], "Updated Bundle")
        self.assertEqual(call_args["bundle_type"], "MANUAL")
        self.assertEqual(call_args["state"], "DRAFT")
        self.assertEqual(call_args["managed_by"], "WAGTAIL")

        # Content should be added separately
        self.mock_client.add_content_to_bundle.assert_called_once()
        content_call_args = self.mock_client.add_content_to_bundle.call_args[0]
        self.assertEqual(content_call_args[0], "api-bundle-456")  # bundle_id
        content_item = content_call_args[1]
        self.assertEqual(content_item["content_type"], "DATASET")
        self.assertEqual(content_item["metadata"]["dataset_id"], dataset.namespace)

        # Bundle should have the API ID set
        self.assertEqual(bundle.bundle_api_content_id, "api-bundle-456")

    def test_save_existing_bundle_with_existing_api_id_does_not_call_api(self):
        """Test that editing an existing bundle that already has an API ID doesn't call create_bundle."""
        # Create an existing bundle with API ID
        existing_bundle = BundleFactory(name="Existing Bundle", bundle_api_content_id="existing-api-id")
        dataset = DatasetFactory(id=123, title="Test Dataset")

        raw_data = {
            "name": "Updated Bundle",
            "status": BundleStatus.DRAFT,
            "bundled_pages": inline_formset([]),
            "bundled_datasets": inline_formset([{"dataset": dataset.id}]),
            "teams": inline_formset([]),
        }

        form = self.form_class(instance=existing_bundle, data=nested_form_data(raw_data), for_user=self.approver)

        self.assertTrue(form.is_valid())
        bundle = form.save()

        # API should NOT be called for bundles that already have an API ID
        self.mock_client.create_bundle.assert_not_called()
        self.assertEqual(bundle.bundle_api_content_id, "existing-api-id")

    def test_status_change__calls_update_state_api(self):
        """Test that updating bundle status calls the Dataset API."""
        existing_bundle = BundleFactory(name="Existing Bundle", bundle_api_content_id="api-bundle-123")
        dataset = DatasetFactory(id=123, title="Test Dataset")
        BundleDataset.objects.create(parent=existing_bundle, dataset=dataset)

        self.mock_client.update_bundle_state.return_value = {"status": "success"}

        raw_data = {
            "name": "Updated Bundle",
            "status": BundleStatus.APPROVED,
            "bundled_pages": inline_formset([]),
            "bundled_datasets": inline_formset([{"dataset": dataset.id}]),
            "teams": inline_formset([]),
        }

        form = self.form_class(instance=existing_bundle, data=nested_form_data(raw_data), for_user=self.approver)

        self.assertTrue(form.is_valid())
        bundle = form.save()

        # API should be called to update status
        self.mock_client.update_bundle_state.assert_called_once_with("api-bundle-123", BundleStatus.APPROVED)
        self.assertEqual(bundle.status, BundleStatus.APPROVED)

    def test_status_change__with_api_error_raises_validation_error(self):
        existing_bundle = BundleFactory(name="Existing Bundle", bundle_api_content_id="api-bundle-123")
        dataset = DatasetFactory(id=123, title="Test Dataset")
        BundleDataset.objects.create(parent=existing_bundle, dataset=dataset)

        self.mock_client.update_bundle_state.side_effect = BundleAPIClientError("API Error")

        raw_data = {
            "name": "Updated Bundle",
            "status": BundleStatus.APPROVED,
            "bundled_pages": inline_formset([]),
            "bundled_datasets": inline_formset([{"dataset": dataset.id}]),
            "teams": inline_formset([]),
        }

        form = self.form_class(instance=existing_bundle, data=nested_form_data(raw_data), for_user=self.approver)

        self.assertTrue(form.is_valid())
        with self.assertRaises(ValidationError) as context:
            form.save()
        self.assertEqual(context.exception.message, "Could not communicate with the Dataset API")

    def test_add_dataset_to_existing_bundle__calls_add_content_api(self):
        existing_bundle = BundleFactory(name="Existing Bundle", bundle_api_content_id="api-bundle-123")
        dataset = DatasetFactory(id=123, title="Test Dataset")

        # Mock the API response for adding content
        mock_response = {
            "id": "api-bundle-123",
            "title": "Test Bundle",
            "bundle_type": "MANUAL",
            "contents": [
                {
                    "id": "content-123",
                    "content_type": "DATASET",
                    "metadata": {
                        "dataset_id": dataset.namespace,
                        "edition_id": dataset.edition,
                        "version_id": dataset.version,
                    },
                }
            ],
        }
        self.mock_client.add_content_to_bundle.return_value = mock_response

        raw_data = {
            "name": "Updated Bundle",
            "status": BundleStatus.DRAFT,
            "bundled_pages": inline_formset([]),
            "bundled_datasets": inline_formset([{"dataset": dataset.id}]),
            "teams": inline_formset([]),
        }

        form = self.form_class(instance=existing_bundle, data=nested_form_data(raw_data), for_user=self.approver)

        self.assertTrue(form.is_valid())
        form.save()

        # API should be called to add content
        self.mock_client.add_content_to_bundle.assert_called_once()
        call_args = self.mock_client.add_content_to_bundle.call_args[0]
        self.assertEqual(call_args[0], "api-bundle-123")
        content_item = call_args[1]
        self.assertEqual(content_item["content_type"], "DATASET")
        self.assertEqual(content_item["metadata"]["dataset_id"], dataset.namespace)

    def test_add_dataset_to_existing_bundle__with_api_error_raises_validation_error(self):
        existing_bundle = BundleFactory(name="Existing Bundle", bundle_api_content_id="api-bundle-123")
        dataset = DatasetFactory(id=123, title="Test Dataset")

        self.mock_client.add_content_to_bundle.side_effect = BundleAPIClientError("API Error")

        raw_data = {
            "name": "Updated Bundle",
            "status": BundleStatus.DRAFT,
            "bundled_pages": inline_formset([]),
            "bundled_datasets": inline_formset([{"dataset": dataset.id}]),
            "teams": inline_formset([]),
        }

        form = self.form_class(instance=existing_bundle, data=nested_form_data(raw_data), for_user=self.approver)

        self.assertTrue(form.is_valid())
        with self.assertRaises(ValidationError) as context:
            form.save()
        self.assertEqual(context.exception.message, "Could not communicate with the Dataset API")

    def test_remove_dataset__calls_delete_content_api(self):
        """Test that removing datasets calls the delete content API."""
        bundle = BundleFactory(name="Existing Bundle", bundle_api_content_id="api-bundle-123")
        dataset1 = DatasetFactory(id=123, title="Dataset 1")
        dataset2 = DatasetFactory(id=456, title="Dataset 2")

        bundle_dataset1 = BundleDataset.objects.create(
            parent=bundle, dataset=dataset1, bundle_api_content_id="content-123"
        )
        bundle_dataset2 = BundleDataset.objects.create(
            parent=bundle, dataset=dataset2, bundle_api_content_id="content-456"
        )

        self.mock_client.delete_content_from_bundle.return_value = {"status": "success"}

        # Remove dataset1, keep dataset2
        raw_data = {
            "name": "Updated Bundle",
            "status": BundleStatus.DRAFT,
            "bundled_pages": inline_formset([]),
            "bundled_datasets": inline_formset(
                [
                    {"id": bundle_dataset1.pk, "dataset": dataset1.pk},
                    {"id": bundle_dataset2.pk, "dataset": dataset2.pk, "DELETE": 1},
                ],
                initial=2,
            ),
            "teams": inline_formset([]),
        }

        form = self.form_class(instance=bundle, data=nested_form_data(raw_data), for_user=self.approver)

        self.assertTrue(form.is_valid())
        form.save()

        # API should be called to delete content
        self.mock_client.delete_content_from_bundle.assert_called_once_with("api-bundle-123", "content-456")

    def test_remove_all_datasets__deletes_bundle_from_api(self):
        """Test that removing all datasets from a bundle deletes it from the API."""
        existing_bundle = BundleFactory(name="Existing Bundle", bundle_api_content_id="api-bundle-123")
        dataset = DatasetFactory(id=123, title="Test Dataset")
        bundle_dataset = BundleDataset.objects.create(parent=existing_bundle, dataset=dataset)

        self.mock_client.delete_bundle.return_value = {"status": "success"}

        raw_data = {
            "name": "Updated Bundle",
            "status": BundleStatus.DRAFT,
            "bundled_pages": inline_formset([]),
            "bundled_datasets": inline_formset(
                [{"id": bundle_dataset.pk, "dataset": dataset.pk, "DELETE": 1}], initial=1
            ),
            "teams": inline_formset([]),
        }

        form = self.form_class(instance=existing_bundle, data=nested_form_data(raw_data), for_user=self.approver)

        self.assertTrue(form.is_valid())
        bundle = form.save()

        # API should be called to delete bundle
        self.mock_client.delete_bundle.assert_called_once_with("api-bundle-123")
        self.assertIsNone(bundle.bundle_api_content_id)

    def test_remove_all_datasets__with_api_error_raises_validation_error(self):
        bundle = BundleFactory(name="Existing Bundle", bundle_api_content_id="api-bundle-123")
        dataset = DatasetFactory(id=123, title="Test Dataset")
        bundle_dataset = BundleDataset.objects.create(parent=bundle, dataset=dataset)

        self.mock_client.delete_bundle.side_effect = BundleAPIClientError("API Error")

        raw_data = {
            "name": "Updated Bundle",
            "status": BundleStatus.DRAFT,
            "bundled_pages": inline_formset([]),
            "bundled_datasets": inline_formset(
                [{"id": bundle_dataset.pk, "dataset": dataset.pk, "DELETE": 1}], initial=1
            ),
            "teams": inline_formset([]),
        }

        form = self.form_class(instance=bundle, data=nested_form_data(raw_data), for_user=self.approver)

        self.assertTrue(form.is_valid())
        with self.assertRaises(ValidationError) as context:
            form.save()
        self.assertEqual(context.exception.message, "Could not communicate with the Dataset API")

    def test_add_team__calls_update_bundle_api(self):
        """Test that adding a team to a bundle calls the API to update preview teams."""
        existing_bundle = BundleFactory(name="Existing Bundle", bundle_api_content_id="api-bundle-123")
        team = TeamFactory(identifier="team-identifier-1")

        self.mock_client.update_bundle.return_value = {"status": "success"}

        raw_data = {
            "name": "Updated Bundle",
            "status": BundleStatus.DRAFT,
            "bundled_pages": inline_formset([]),
            "bundled_datasets": inline_formset([]),
            "teams": inline_formset([{"team": team.id}]),
        }

        form = self.form_class(instance=existing_bundle, data=nested_form_data(raw_data), for_user=self.approver)

        self.assertTrue(form.is_valid())
        form.save()

        # API should be called to update preview teams
        self.mock_client.update_bundle.assert_called_once()
        call_args = self.mock_client.update_bundle.call_args
        self.assertEqual(call_args[1]["bundle_id"], "api-bundle-123")
        bundle_data = call_args[1]["bundle_data"]
        self.assertEqual(bundle_data["preview_teams"], [{"id": "team-identifier-1"}])

    def test_add_team__with_api_error_raises_validation_error(self):
        """Test that API errors during team sync raise ValidationError."""
        existing_bundle = BundleFactory(name="Existing Bundle", bundle_api_content_id="api-bundle-123")
        team = TeamFactory(identifier="team-identifier-1")

        self.mock_client.update_bundle.side_effect = BundleAPIClientError("API Error")

        raw_data = {
            "name": "Updated Bundle",
            "status": BundleStatus.DRAFT,
            "bundled_pages": inline_formset([]),
            "bundled_datasets": inline_formset([]),
            "teams": inline_formset([{"team": team.id}]),
        }

        form = self.form_class(instance=existing_bundle, data=nested_form_data(raw_data), for_user=self.approver)

        self.assertTrue(form.is_valid())
        with self.assertRaises(ValidationError) as context:
            form.save()
        self.assertEqual(context.exception.message, "Could not communicate with the Dataset API")

    def test_save_bundle__extracts_content_id_from_response(self):
        existing_bundle = BundleFactory(name="Existing Bundle", bundle_api_content_id="api-bundle-123")
        dataset = DatasetFactory(id=123, title="Test Dataset")

        # Mock API response with content in the bundle
        mock_response = {
            "bundle_id": "api-bundle-123",
            "content_type": "DATASET",
            "metadata": {
                "dataset_id": dataset.namespace,
                "edition_id": dataset.edition,
                "version_id": dataset.version,
            },
            "id": "content-456",
        }
        self.mock_client.add_content_to_bundle.return_value = mock_response

        raw_data = {
            "name": "Updated Bundle",
            "status": BundleStatus.DRAFT,
            "bundled_pages": inline_formset([]),
            "bundled_datasets": inline_formset([{"dataset": dataset.id}]),
            "teams": inline_formset([]),
        }

        form = self.form_class(instance=existing_bundle, data=nested_form_data(raw_data), for_user=self.approver)

        self.assertTrue(form.is_valid())
        form.save()

        bundle_dataset = BundleDataset.objects.get(parent=existing_bundle, dataset=dataset)
        self.assertEqual(bundle_dataset.bundle_api_content_id, "content-456")

    def test_save_bundle_no_datasets_skips_api_calls(self):
        """Test that bundles without datasets don't trigger API calls."""
        existing_bundle = BundleFactory(name="Existing Bundle")

        raw_data = {
            "name": "Updated Bundle",
            "status": BundleStatus.DRAFT,
            "bundled_pages": inline_formset([]),
            "bundled_datasets": inline_formset([]),
            "teams": inline_formset([]),
        }

        form = self.form_class(instance=existing_bundle, data=nested_form_data(raw_data), for_user=self.approver)

        self.assertTrue(form.is_valid())
        form.save()

        # No API calls should be made
        self.mock_client.create_bundle.assert_not_called()
        self.mock_client.update_bundle_state.assert_not_called()
        self.mock_client.add_content_to_bundle.assert_not_called()
        self.mock_client.delete_bundle.assert_not_called()
        self.mock_client.update_bundle.assert_not_called()


@override_settings(DIS_DATASETS_BUNDLE_API_ENABLED=False)
class BundleFormSaveWithDatasetAPIDisabledTestCase(TestCase):
    """Test cases for the BundleAdminForm save method when API is disabled."""

    @classmethod
    def setUpTestData(cls):
        cls.form_class = get_edit_handler(Bundle).get_form_class()
        cls.approver = UserFactory()

    def setUp(self):
        self.patcher = patch("cms.bundles.forms.BundleAPIClient")
        self.mock_client_class = self.patcher.start()
        self.mock_client = self.mock_client_class.return_value

    def tearDown(self):
        self.patcher.stop()

    def test_save_new_bundle_with_datasets_does_not_call_api_when_disabled(self):
        """Test that saving a new bundle with datasets doesn't call the API when disabled."""
        dataset = DatasetFactory(id=123, title="Test Dataset")
        raw_data = {
            "name": "Test Bundle",
            "status": BundleStatus.DRAFT,
            "bundled_pages": inline_formset([]),
            "bundled_datasets": inline_formset([{"dataset": dataset.id}]),
            "teams": inline_formset([]),
        }

        form = self.form_class(data=nested_form_data(raw_data), for_user=self.approver)

        self.assertTrue(form.is_valid())
        bundle = form.save()

        # API should not be called when disabled
        self.mock_client.create_bundle.assert_not_called()
        self.assertIsNone(bundle.bundle_api_content_id)
