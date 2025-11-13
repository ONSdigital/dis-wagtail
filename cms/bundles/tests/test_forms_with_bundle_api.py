from http import HTTPStatus
from typing import Any
from unittest.mock import patch

import responses
from django.conf import settings
from django.core.exceptions import ValidationError
from django.test import TestCase, override_settings
from wagtail.admin.panels import get_edit_handler
from wagtail.test.utils.form_data import inline_formset, nested_form_data

from cms.bundles.clients.api import BundleAPIClientError
from cms.bundles.enums import BundleStatus
from cms.bundles.models import Bundle, BundleDataset
from cms.bundles.tests.factories import BundleDatasetFactory, BundleFactory
from cms.datasets.tests.factories import DatasetFactory
from cms.teams.tests.factories import TeamFactory
from cms.users.tests.factories import UserFactory

# TODO: Refactor these tests to patch and assert calls on the BundleAPIClient
# instead of mocking HTTP via `responses`. These tests should focus on verifying
# that the form/service logic invokes the correct client methods with the expected
# arguments and sequencing. Low-level HTTP behaviour (method, headers, payload,
# ETag handling, etc.) should be covered separately in test_client_api.py.


@override_settings(DIS_DATASETS_BUNDLE_API_ENABLED=True, BUNDLE_DATASET_STATUS_VALIDATION_ENABLED=True)
class BundleFormSaveWithBundleAPITestCase(TestCase):
    """Test cases for the BundleAdminForm save method."""

    @classmethod
    def setUpTestData(cls):
        cls.form_class = get_edit_handler(Bundle).get_form_class()
        cls.approver = UserFactory()

        cls.bundle_api_id = "api-bundle-123"
        cls.bundle = BundleFactory(bundle_api_bundle_id=cls.bundle_api_id, bundle_api_etag="etag-123")

        cls.base_api_url = settings.DIS_DATASETS_BUNDLE_API_BASE_URL
        cls.bundle_endpoint = f"{cls.base_api_url}/bundles"
        cls.update_bundle_endpoint = f"{cls.base_api_url}/bundles/{cls.bundle_api_id}"
        cls.delete_endpoint = f"{cls.base_api_url}/bundles/{cls.bundle_api_id}"
        cls.content_endpoint = f"{cls.base_api_url}/bundles/{cls.bundle_api_id}/contents"
        cls.status_endpoint = f"{cls.base_api_url}/bundles/{cls.bundle_api_id}/state"
        cls.content_item_json = {
            "id": "content-123",
            "metadata": {
                "dataset_id": "cpih",
                "edition_id": "time-series",
                "version_id": 1,
            },
            "etag_header": "etag-123",
        }

        cls.dataset = DatasetFactory()

    @responses.activate
    def test_save_new_bundle_without_datasets_does_not_call_api(self):
        """Test that saving a new bundle without datasets doesn't call the API."""
        responses.post(self.bundle_endpoint, json={}, status=HTTPStatus.OK)

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
        responses.assert_call_count(self.bundle_endpoint, 0)
        self.assertEqual(bundle.bundle_api_bundle_id, "")

    @responses.activate
    def test_save_new_bundle_with_datasets_calls_api(self):
        """Test that saving a new bundle with datasets calls the API."""
        responses.post(
            self.bundle_endpoint,
            json={"id": self.bundle_api_id, "etag_header": "etag"},
            status=HTTPStatus.OK,
            headers={"ETag": "etag"},
        )

        responses.post(
            self.content_endpoint, json=self.content_item_json, status=HTTPStatus.OK, headers={"ETag": "etag-123"}
        )

        dataset = DatasetFactory(namespace="cpih", edition="time-series", version=1)
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
        responses.assert_call_count(self.bundle_endpoint, 1)
        responses.assert_call_count(self.content_endpoint, 1)

        # Bundle should have the API ID set
        self.assertEqual(bundle.bundle_api_bundle_id, self.bundle_api_id)
        self.assertEqual(bundle.bundle_api_etag, "etag-123")
        self.assertEqual(bundle.bundled_datasets.first().bundle_api_content_id, "content-123")

    @responses.activate
    def test_save_existing_bundle_uses_standard_behavior(self):
        """Test that saving an existing bundle uses standard Django form behavior."""
        bundle = BundleFactory(name="Existing Bundle")

        raw_data = {
            "name": "Updated Bundle",
            "status": BundleStatus.DRAFT,
            "bundled_pages": inline_formset([]),
            "bundled_datasets": inline_formset([]),
            "teams": inline_formset([]),
        }

        form = self.form_class(instance=bundle, data=nested_form_data(raw_data), for_user=self.approver)

        self.assertTrue(form.is_valid())
        bundle = form.save()

        # API should not be called for existing bundles in form save
        responses.assert_call_count(f"{self.base_api_url}/bundles", 0)
        self.assertEqual(bundle.name, "Updated Bundle")

    @responses.activate
    def test_save_new_bundle_with_datasets_api_error_raises_validation_error(self):
        """Test that API errors during bundle creation don't prevent saving."""
        responses.post(self.bundle_endpoint, json={"status": "error"}, status=HTTPStatus.INTERNAL_SERVER_ERROR)
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
        self.assertEqual(context.exception.message, "Could not communicate with the Bundle API")

    @responses.activate
    def test_save_new_bundle_with_datasets_no_api_id_returned(self):
        """Test handling when API doesn't return an ID."""
        responses.post(
            self.bundle_endpoint, json={"message": "no id here"}, status=HTTPStatus.OK, headers={"ETag": "etag"}
        )

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

        self.assertEqual(context.exception.message, "Could not communicate with the Bundle API")

        # API should be called
        responses.assert_call_count(self.bundle_endpoint, 1)

    @responses.activate
    def test_save_existing_bundle_with_first_dataset_calls_api(self):
        """Test that editing an existing bundle to add its first dataset calls the API."""
        responses.post(
            self.bundle_endpoint,
            json={"id": self.bundle_api_id, "etag_header": "etag"},
            status=HTTPStatus.OK,
            headers={"ETag": "etag"},
        )

        responses.post(
            self.content_endpoint, json=self.content_item_json, status=HTTPStatus.OK, headers={"ETag": "etag-123"}
        )

        # Create an existing bundle without datasets
        bundle = BundleFactory(name="Existing Bundle", bundle_api_bundle_id="", bundle_api_etag="")
        dataset = DatasetFactory(namespace="cpih", edition="time-series", version=1)

        raw_data = {
            "name": "Updated Bundle",
            "status": BundleStatus.DRAFT,
            "bundled_pages": inline_formset([]),
            "bundled_datasets": inline_formset([{"dataset": dataset.id}]),
            "teams": inline_formset([]),
        }

        form = self.form_class(instance=bundle, data=nested_form_data(raw_data), for_user=self.approver)

        self.assertTrue(form.is_valid())
        bundle = form.save()

        responses.assert_call_count(self.bundle_endpoint, 1)
        responses.assert_call_count(self.content_endpoint, 1)

        # Bundle should have the API fields set
        self.assertEqual(bundle.bundle_api_bundle_id, self.bundle_api_id)
        self.assertEqual(bundle.bundle_api_etag, "etag-123")
        self.assertEqual(bundle.bundled_datasets.first().bundle_api_content_id, "content-123")

    @responses.activate
    def test_save_existing_bundle_with_existing_api_id_does_not_call_api(self):
        """Test that editing an existing bundle that already has an API ID doesn't call create_bundle."""
        bundle = BundleFactory(name="Existing Bundle", bundle_api_bundle_id=self.bundle_api_id)
        dataset = DatasetFactory(
            namespace="cpih",
            edition="time-series",
            version=1,
        )

        responses.post(
            self.content_endpoint, json=self.content_item_json, status=HTTPStatus.OK, headers={"ETag": "etag-123"}
        )

        raw_data = {
            "name": "Updated Bundle",
            "status": BundleStatus.DRAFT,
            "bundled_pages": inline_formset([]),
            "bundled_datasets": inline_formset([{"dataset": dataset.id}]),
            "teams": inline_formset([]),
        }

        form = self.form_class(instance=bundle, data=nested_form_data(raw_data), for_user=self.approver)

        self.assertTrue(form.is_valid())
        bundle = form.save()

        # API should NOT be called for bundles that already have an API ID
        responses.assert_call_count(self.bundle_endpoint, 0)
        self.assertEqual(bundle.bundle_api_bundle_id, self.bundle_api_id)
        responses.assert_call_count(self.content_endpoint, 1)

    @responses.activate
    def test_status_change__calls_update_state_api(self):
        """Test that updating bundle status calls the Bundle API."""
        BundleDataset.objects.create(parent=self.bundle, dataset=DatasetFactory(), bundle_api_content_id="123")

        mock_response_data = {"id": self.bundle_api_id, "etag_header": "etag-123"}
        responses.put(self.status_endpoint, json=mock_response_data, status=HTTPStatus.OK, headers={"ETag": "etag-123"})

        raw_data = {
            "name": self.bundle.name,
            "status": BundleStatus.IN_REVIEW,
            "bundled_pages": inline_formset([]),
            "bundled_datasets": inline_formset([]),
            "teams": inline_formset([]),
        }

        form = self.form_class(instance=self.bundle, data=nested_form_data(raw_data), for_user=self.approver)

        self.assertTrue(form.is_valid())
        bundle = form.save()

        # API should be called to update status
        responses.assert_call_count(self.status_endpoint, 1)
        self.assertEqual(bundle.status, BundleStatus.IN_REVIEW)
        self.assertEqual(bundle.bundle_api_etag, "etag-123")

    @responses.activate
    def test_status_change__with_api_error_raises_validation_error(self):
        responses.put(self.status_endpoint, json={"status": "error"}, status=HTTPStatus.NOT_FOUND)

        BundleDataset.objects.create(parent=self.bundle, dataset=self.dataset)
        raw_data = {
            "name": "Updated Bundle",
            "status": BundleStatus.IN_REVIEW,
            "bundled_pages": inline_formset([]),
            "bundled_datasets": inline_formset([]),
            "teams": inline_formset([]),
        }
        form = self.form_class(instance=self.bundle, data=nested_form_data(raw_data), for_user=self.approver)

        self.assertTrue(form.is_valid())
        with self.assertRaises(ValidationError) as context:
            form.save()
        self.assertEqual(context.exception.message, "Could not communicate with the Bundle API")

    @responses.activate
    def test_remove_dataset__calls_delete_content_api(self):
        """Test that removing datasets calls the delete content API."""
        dataset_2 = DatasetFactory(id=456, title="Dataset 2")

        bundle_dataset_1 = BundleDataset.objects.create(
            parent=self.bundle, dataset=self.dataset, bundle_api_content_id="content-123"
        )
        bundle_dataset_2 = BundleDataset.objects.create(
            parent=self.bundle, dataset=dataset_2, bundle_api_content_id="content-456"
        )

        content_endpoint = f"{self.base_api_url}/bundles/api-bundle-123/contents/content-456"
        responses.delete(content_endpoint, status=HTTPStatus.NO_CONTENT, headers={"ETag": "etag-after-delete"})

        # Remove dataset_1, keep dataset_2
        raw_data = {
            "name": "Updated Bundle",
            "status": BundleStatus.DRAFT,
            "bundled_pages": inline_formset([]),
            "bundled_datasets": inline_formset(
                [
                    {"id": bundle_dataset_1.pk, "dataset": self.dataset.pk},
                    {"id": bundle_dataset_2.pk, "dataset": dataset_2.pk, "DELETE": 1},
                ],
                initial=2,
            ),
            "teams": inline_formset([]),
        }

        form = self.form_class(instance=self.bundle, data=nested_form_data(raw_data), for_user=self.approver)

        self.assertTrue(form.is_valid())
        form.save()

        responses.assert_call_count(content_endpoint, 1)
        self.assertEqual(self.bundle.bundle_api_etag, "etag-after-delete")

    @responses.activate
    def test_remove_all_datasets__deletes_bundle_from_api(self):
        """Test that removing all datasets from a bundle deletes it from the API."""
        bundle_dataset = BundleDataset.objects.create(parent=self.bundle, dataset=self.dataset)

        responses.delete(self.delete_endpoint, status=HTTPStatus.NO_CONTENT)

        raw_data = {
            "name": "Updated Bundle",
            "status": BundleStatus.DRAFT,
            "bundled_pages": inline_formset([]),
            "bundled_datasets": inline_formset(
                [{"id": bundle_dataset.pk, "dataset": self.dataset.pk, "DELETE": 1}], initial=1
            ),
            "teams": inline_formset([]),
        }

        form = self.form_class(instance=self.bundle, data=nested_form_data(raw_data), for_user=self.approver)

        self.assertTrue(form.is_valid())
        bundle = form.save()

        # API should be called to delete bundle
        responses.assert_call_count(self.delete_endpoint, 1)
        self.assertEqual(bundle.bundle_api_bundle_id, "")
        self.assertEqual(bundle.bundle_api_etag, "")

    @responses.activate
    def test_remove_all_datasets__with_api_error_raises_validation_error(self):
        bundle_dataset = BundleDataset.objects.create(parent=self.bundle, dataset=self.dataset)

        responses.delete(self.delete_endpoint, status=HTTPStatus.NOT_FOUND)

        raw_data = {
            "name": "Updated Bundle",
            "status": BundleStatus.DRAFT,
            "bundled_pages": inline_formset([]),
            "bundled_datasets": inline_formset(
                [{"id": bundle_dataset.pk, "dataset": self.dataset.pk, "DELETE": 1}], initial=1
            ),
            "teams": inline_formset([]),
        }

        form = self.form_class(instance=self.bundle, data=nested_form_data(raw_data), for_user=self.approver)

        self.assertTrue(form.is_valid())
        with self.assertRaises(ValidationError) as context:
            form.save()
        self.assertEqual(context.exception.message, "Could not communicate with the Bundle API")

    @responses.activate
    def test_add_dataset_no_content_id_from_bundle_response_raises_validation_error(self):
        """Test that missing content ID from API response for the added dataset raises ValidationError."""
        bundle = BundleFactory(name="Bundle", bundle_api_bundle_id=self.bundle_api_id)
        dataset = DatasetFactory(
            namespace="cpih",
            edition="time-series",
            version=2,  # different version compared to self.content_item_json
        )

        responses.post(
            self.content_endpoint, json=self.content_item_json, status=HTTPStatus.OK, headers={"ETag": "etag-123"}
        )

        raw_data = {
            "name": "Updated Bundle",
            "status": BundleStatus.DRAFT,
            "bundled_pages": inline_formset([]),
            "bundled_datasets": inline_formset([{"dataset": dataset.id}]),
            "teams": inline_formset([]),
        }

        form = self.form_class(instance=bundle, data=nested_form_data(raw_data), for_user=self.approver)

        self.assertTrue(form.is_valid())

        with self.assertRaises(ValidationError) as context:
            form.save()
        self.assertEqual(context.exception.message, "Bundle API did not return an ID for the added content")

    @responses.activate
    def test_add_team__calls_update_bundle_api(self):
        """Test that adding a team to a bundle calls the API to update preview teams."""
        team = TeamFactory(identifier="team-identifier-1")

        responses.put(
            self.update_bundle_endpoint, json={"etag_header": "etag"}, status=HTTPStatus.OK, headers={"ETag": "etag"}
        )

        raw_data = {
            "name": "Updated Bundle",
            "status": BundleStatus.DRAFT,
            "bundled_pages": inline_formset([]),
            "bundled_datasets": inline_formset([]),
            "teams": inline_formset([{"team": team.id}]),
        }

        form = self.form_class(instance=self.bundle, data=nested_form_data(raw_data), for_user=self.approver)

        self.assertTrue(form.is_valid())
        bundle = form.save()

        # API should be called to update preview teams
        responses.assert_call_count(self.update_bundle_endpoint, 1)
        self.assertEqual(bundle.bundle_api_etag, "etag")

    @responses.activate
    def test_add_team__with_api_error_raises_validation_error(self):
        """Test that API errors during team sync raise ValidationError."""
        team = TeamFactory(identifier="team-identifier-1")

        responses.put(self.update_bundle_endpoint, status=HTTPStatus.INTERNAL_SERVER_ERROR)

        raw_data = {
            "name": "Updated Bundle",
            "status": BundleStatus.DRAFT,
            "bundled_pages": inline_formset([]),
            "bundled_datasets": inline_formset([]),
            "teams": inline_formset([{"team": team.id}]),
        }

        form = self.form_class(instance=self.bundle, data=nested_form_data(raw_data), for_user=self.approver)

        self.assertTrue(form.is_valid())
        with self.assertRaises(ValidationError) as context:
            form.save()
        self.assertEqual(context.exception.message, "Could not communicate with the Bundle API")

    @patch("cms.bundles.forms.BundleAPIClient")
    def test_save_bundle_no_datasets_skips_api_calls(self, mock_client):
        """Test that bundles without datasets don't trigger API calls."""
        bundle = BundleFactory()

        raw_data = {
            "name": "Updated Bundle",
            "status": BundleStatus.DRAFT,
            "bundled_pages": inline_formset([]),
            "bundled_datasets": inline_formset([]),
            "teams": inline_formset([]),
        }

        form = self.form_class(instance=bundle, data=nested_form_data(raw_data), for_user=self.approver)

        self.assertTrue(form.is_valid())
        form.save()

        # No API calls should be made
        mock_client.create_bundle.assert_not_called()
        mock_client.update_bundle_state.assert_not_called()
        mock_client.add_content_to_bundle.assert_not_called()
        mock_client.delete_bundle.assert_not_called()
        mock_client.update_bundle.assert_not_called()


@override_settings(DIS_DATASETS_BUNDLE_API_ENABLED=False)
class BundleFormSaveWithBundleAPIDisabledTestCase(TestCase):
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
        self.assertEqual(bundle.bundle_api_bundle_id, "")


@override_settings(DIS_DATASETS_BUNDLE_API_ENABLED=True, BUNDLE_DATASET_STATUS_VALIDATION_ENABLED=True)
class BundleDatasetValidationTestCase(TestCase):
    """Test cases for dataset validation in the BundleAdminForm."""

    @classmethod
    def setUpTestData(cls):
        cls.bundle = BundleFactory(name="Test Bundle")
        cls.form_class = get_edit_handler(Bundle).get_form_class()
        cls.approver = UserFactory()

    def setUp(self):
        self.patcher = patch("cms.bundles.forms.BundleAPIClient")
        self.mock_client_class = self.patcher.start()
        self.mock_client = self.mock_client_class.return_value

    def tearDown(self):
        self.patcher.stop()

    def raw_form_data_with_dataset(self, dataset: "DatasetFactory") -> dict[str, Any]:
        """Returns raw form data with a dataset."""
        bundle_dataset = BundleDatasetFactory(parent=self.bundle, dataset=dataset)
        raw_data = {
            "name": self.bundle.name,
            "status": BundleStatus.APPROVED,
            "bundled_pages": inline_formset([]),
            "bundled_datasets": inline_formset(
                [{"id": bundle_dataset.id, "dataset": bundle_dataset.dataset_id, "ORDER": "1"}], initial=1
            ),
            "teams": inline_formset([]),
        }

        return raw_data

    def test_dataset_validation_approved_dataset_passes(self):
        """Test that approved datasets pass validation."""
        dataset = DatasetFactory(id=123)
        self.bundle.bundle_api_bundle_id = "test-bundle-123"
        self.bundle.save(update_fields=["bundle_api_bundle_id"])

        self.mock_client.get_bundle_contents.return_value = {
            "items": [
                {
                    "id": "content-1",
                    "state": "APPROVED",
                    "metadata": {
                        "dataset_id": dataset.namespace,
                        "edition_id": dataset.edition,
                        "version_id": dataset.version,
                    },
                }
            ],
            "etag_header": "etag",
        }

        raw_data = self.raw_form_data_with_dataset(dataset)
        form = self.form_class(instance=self.bundle, data=nested_form_data(raw_data), for_user=self.approver)

        self.assertTrue(form.is_valid())
        self.mock_client.get_bundle_contents.assert_called_once_with("test-bundle-123")

    def test_dataset_validation_unapproved_dataset_fails(self):
        """Test that unapproved datasets fail validation."""
        dataset = DatasetFactory(id=123, title="Test Dataset")
        self.bundle.bundle_api_bundle_id = "test-bundle-123"
        self.bundle.save(update_fields=["bundle_api_bundle_id"])

        self.mock_client.get_bundle_contents.return_value = {
            "items": [
                {
                    "id": "content-1",
                    "state": "DRAFT",
                    "metadata": {
                        "dataset_id": dataset.namespace,
                        "edition_id": dataset.edition,
                        "version_id": dataset.version,
                    },
                }
            ],
            "etag_header": "etag",
        }

        raw_data = self.raw_form_data_with_dataset(dataset)
        form = self.form_class(instance=self.bundle, data=nested_form_data(raw_data), for_user=self.approver)

        self.assertFalse(form.is_valid())
        self.assertFormError(
            form,
            None,
            [
                "Cannot approve the bundle with 1 dataset not ready to be published: "
                f"Test Dataset (Edition: {dataset.edition}, Status: DRAFT)"
            ],
        )

    def test_dataset_validation_multiple_datasets_mixed_statuses(self):
        """Test validation with multiple datasets having different statuses."""
        dataset_1 = DatasetFactory(id=123, title="Approved Dataset")
        dataset_2 = DatasetFactory(id=124, title="Draft Dataset")
        bundled_dataset_1 = BundleDatasetFactory(parent=self.bundle, dataset=dataset_1)
        bundled_dataset_2 = BundleDatasetFactory(parent=self.bundle, dataset=dataset_2)
        self.bundle.bundle_api_bundle_id = "test-bundle-123"
        self.bundle.save(update_fields=["bundle_api_bundle_id"])

        self.mock_client.get_bundle_contents.return_value = {
            "items": [
                {
                    "id": "content-1",
                    "state": "APPROVED",
                    "metadata": {
                        "dataset_id": dataset_1.namespace,
                        "edition_id": dataset_1.edition,
                        "version_id": dataset_1.version,
                    },
                },
                {
                    "id": "content-2",
                    "state": "DRAFT",
                    "metadata": {
                        "dataset_id": dataset_2.namespace,
                        "edition_id": dataset_2.edition,
                        "version_id": dataset_2.version,
                    },
                },
            ],
            "etag_header": "etag",
        }

        raw_data = {
            "name": "Test Bundle",
            "status": BundleStatus.APPROVED,
            "bundled_pages": inline_formset([]),
            "bundled_datasets": inline_formset(
                [
                    {"id": bundled_dataset_1.id, "dataset": bundled_dataset_1.dataset_id, "ORDER": "1"},
                    {"id": bundled_dataset_2.id, "dataset": bundled_dataset_2.dataset_id, "ORDER": "2"},
                ],
                initial=2,
            ),
            "teams": inline_formset([]),
        }

        form = self.form_class(instance=self.bundle, data=nested_form_data(raw_data), for_user=self.approver)

        self.assertFalse(form.is_valid())
        self.assertFormError(
            form,
            None,
            [
                "Cannot approve the bundle with 1 dataset not ready to be published: "
                f"Draft Dataset (Edition: {dataset_2.edition}, Status: DRAFT)"
            ],
        )

    def test_dataset_validation_multiple_datasets_not_ready(self):
        """Test that multiple datasets not ready shows proper pluralization."""
        dataset_1 = DatasetFactory(id=123, title="Draft Dataset 1")
        dataset_2 = DatasetFactory(id=124, title="Draft Dataset 2")
        bundle_dataset_1 = BundleDatasetFactory(parent=self.bundle, dataset=dataset_1)
        bundle_dataset_2 = BundleDatasetFactory(parent=self.bundle, dataset=dataset_2)
        self.bundle.bundle_api_bundle_id = "test-bundle-123"
        self.bundle.save(update_fields=["bundle_api_bundle_id"])

        self.mock_client.get_bundle_contents.return_value = {
            "items": [
                {
                    "id": "content-1",
                    "state": "DRAFT",
                    "metadata": {
                        "dataset_id": dataset_1.namespace,
                        "edition_id": dataset_1.edition,
                        "version_id": dataset_1.version,
                    },
                },
                {
                    "id": "content-2",
                    "state": "DRAFT",
                    "metadata": {
                        "dataset_id": dataset_2.namespace,
                        "edition_id": dataset_2.edition,
                        "version_id": dataset_2.version,
                    },
                },
            ],
            "etag_header": "etag",
        }

        raw_data = {
            "name": "Test Bundle",
            "status": BundleStatus.APPROVED,
            "bundled_pages": inline_formset([]),
            "bundled_datasets": inline_formset(
                [
                    {"id": bundle_dataset_1.id, "dataset": bundle_dataset_1.dataset_id, "ORDER": "1"},
                    {"id": bundle_dataset_2.id, "dataset": bundle_dataset_2.dataset_id, "ORDER": "2"},
                ],
                initial=2,
            ),
            "teams": inline_formset([]),
        }

        form = self.form_class(instance=self.bundle, data=nested_form_data(raw_data), for_user=self.approver)

        self.assertFalse(form.is_valid())
        self.assertFormError(
            form,
            None,
            [
                "Cannot approve the bundle with 2 datasets not ready to be published: "
                f"Draft Dataset 1 (Edition: {dataset_1.edition}, Status: DRAFT), "
                f"Draft Dataset 2 (Edition: {dataset_2.edition}, Status: DRAFT)"
            ],
        )

    def test_dataset_validation_api_error_fails_gracefully(self):
        """Test that API errors are handled gracefully."""
        dataset = DatasetFactory(id=123, title="Test Dataset")
        self.bundle.bundle_api_bundle_id = "test-bundle-123"
        self.bundle.save(update_fields=["bundle_api_bundle_id"])

        self.mock_client.get_bundle_contents.side_effect = BundleAPIClientError("API Error")

        raw_data = self.raw_form_data_with_dataset(dataset)
        form = self.form_class(instance=self.bundle, data=nested_form_data(raw_data), for_user=self.approver)

        self.assertFalse(form.is_valid())
        self.assertFormError(
            form,
            None,
            ["Cannot approve the bundle with 1 dataset not ready to be published: Bundle content validation failed"],
        )

    def test_dataset_validation_only_runs_when_approving(self):
        """Test that dataset validation only runs when changing status to APPROVED."""
        dataset = DatasetFactory(id=123)
        self.bundle.bundle_api_bundle_id = "test-bundle-123"
        self.bundle.save(update_fields=["bundle_api_bundle_id"])

        self.mock_client.get_bundle_contents.return_value = {
            "contents": [
                {
                    "id": "content-1",
                    "state": "DRAFT",
                    "metadata": {
                        "dataset_id": dataset.namespace,
                        "edition_id": dataset.edition,
                        "version_id": dataset.version,
                    },
                }
            ]
        }

        raw_data = self.raw_form_data_with_dataset(dataset)
        raw_data["status"] = BundleStatus.IN_REVIEW  # Not approving

        form = self.form_class(instance=self.bundle, data=nested_form_data(raw_data), for_user=self.approver)

        self.assertTrue(form.is_valid())
        self.mock_client.get_bundle_contents.assert_not_called()

    def test_dataset_validation_skipped_when_no_datasets(self):
        """Test that dataset validation is skipped when there are no datasets."""
        raw_data = {
            "name": "Test Bundle",
            "status": BundleStatus.APPROVED,
            "bundled_pages": inline_formset([]),
            "bundled_datasets": inline_formset([]),
            "teams": inline_formset([]),
        }

        form = self.form_class(instance=self.bundle, data=nested_form_data(raw_data), for_user=self.approver)

        self.assertFalse(form.is_valid())  # Should fail because no pages or datasets
        self.mock_client.get_bundle_contents.assert_not_called()

    def test_dataset_validation_skipped_when_no_bundle_api_bundle_id(self):
        """Test that dataset validation is skipped when bundle has no API ID."""
        dataset = DatasetFactory(id=123, title="Test Dataset")
        # Bundle doesn't have bundle_api_bundle_id set
        self.assertEqual(self.bundle.bundle_api_bundle_id, "")

        raw_data = self.raw_form_data_with_dataset(dataset)
        form = self.form_class(instance=self.bundle, data=nested_form_data(raw_data), for_user=self.approver)

        self.assertTrue(form.is_valid())
        self.mock_client.get_bundle_contents.assert_not_called()

    def test_dataset_validation_empty_contents_array(self):
        """Test validation handles empty contents array from API."""
        dataset = DatasetFactory(id=123, title="Test Dataset")
        self.bundle.bundle_api_bundle_id = "test-bundle-123"
        self.bundle.save(update_fields=["bundle_api_bundle_id"])

        self.mock_client.get_bundle_contents.return_value = {"items": [], "etag_header": "etag"}

        raw_data = self.raw_form_data_with_dataset(dataset)
        form = self.form_class(instance=self.bundle, data=nested_form_data(raw_data), for_user=self.approver)

        self.assertTrue(form.is_valid())
        self.mock_client.get_bundle_contents.assert_called_once_with("test-bundle-123")


class BundleDatasetValidationDisabledTestCase(TestCase):
    """Test cases for dataset validation when API or validation is disabled."""

    @classmethod
    def setUpTestData(cls):
        cls.bundle = BundleFactory(name="Test Bundle", bundle_api_bundle_id="test-bundle-123")
        cls.form_class = get_edit_handler(Bundle).get_form_class()
        cls.approver = UserFactory()

    def setUp(self):
        self.patcher = patch("cms.bundles.forms.BundleAPIClient")
        self.mock_client_class = self.patcher.start()
        self.mock_client = self.mock_client_class.return_value

    def tearDown(self):
        self.patcher.stop()

    def _assert_validation_skipped(self):
        """Helper method to assert dataset validation is skipped."""
        bundle_dataset = BundleDatasetFactory(parent=self.bundle)

        raw_data = {
            "name": self.bundle.name,
            "status": BundleStatus.APPROVED,
            "bundled_pages": inline_formset([]),
            "bundled_datasets": inline_formset(
                [{"id": bundle_dataset.id, "dataset": bundle_dataset.dataset_id, "ORDER": "1"}], initial=1
            ),
            "teams": inline_formset([]),
        }

        form = self.form_class(instance=self.bundle, data=nested_form_data(raw_data), for_user=self.approver)

        self.assertTrue(form.is_valid(), form.errors)
        # API client should not be called when disabled
        self.mock_client.get_bundle_contents.assert_not_called()

    @override_settings(DIS_DATASETS_BUNDLE_API_ENABLED=False, BUNDLE_DATASET_STATUS_VALIDATION_ENABLED=True)
    def test_dataset_validation_skipped_when_api_disabled(self):
        """Test that dataset validation is skipped when DIS_DATASETS_BUNDLE_API_ENABLED is False."""
        self._assert_validation_skipped()

    @override_settings(DIS_DATASETS_BUNDLE_API_ENABLED=True, BUNDLE_DATASET_STATUS_VALIDATION_ENABLED=False)
    def test_dataset_validation_skipped_when_validation_flag_disabled(self):
        """Test that dataset validation is skipped when BUNDLE_DATASET_STATUS_VALIDATION_ENABLED is False."""
        self._assert_validation_skipped()
