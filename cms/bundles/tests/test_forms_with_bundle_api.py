from typing import Any
from unittest.mock import MagicMock, patch

import requests
from django.test import TestCase, override_settings
from wagtail.admin.panels import get_edit_handler
from wagtail.test.utils.form_data import inline_formset, nested_form_data

from cms.bundles.clients.api import BundleAPIClient, BundleAPIClientError
from cms.bundles.enums import BundleStatus
from cms.bundles.models import Bundle
from cms.bundles.tests.factories import BundleDatasetFactory, BundleFactory
from cms.datasets.models import Dataset, ONSDatasetApiQuerySet
from cms.datasets.tests.factories import DatasetFactory
from cms.users.tests.factories import UserFactory


def _patch_ons_dataset_api_no_drift() -> Any:
    """Patch the ONS dataset API used by metadata validation to mirror local Dataset rows.

    Returns a mock whose `objects.get(pk=namespace)` resolves to an object exposing the
    same `title`/`description` as the local `Dataset` row, so the metadata-drift check
    finds nothing to flag by default.
    """

    def fake_get(pk: Any = None) -> Any:
        local = Dataset.objects.filter(namespace=pk).first()
        item = MagicMock()
        item.next = None
        item.title = local.title if local else ""
        item.description = local.description if local else ""
        return item

    patcher = patch("cms.bundles.forms.ONSDataset")
    mock_ons = patcher.start()
    mock_ons.objects.get.side_effect = fake_get
    return patcher


@override_settings(DIS_DATASETS_BUNDLE_API_ENABLED=True)
class BundleFormDelegationToBundleSyncServiceTestCase(TestCase):
    """Test that Bundle form delegates to BundleAPISyncService on save()."""

    @classmethod
    def setUpTestData(cls):
        cls.form_class = get_edit_handler(Bundle).get_form_class()
        cls.user = UserFactory()

    def test_save_calls_sync_service_with_expected_args(self):
        """Form should instantiate BundleAPISyncService(bundle, api_client, original_datasets) and call sync()."""
        # Existing bundle with one original dataset to verify snapshot is passed
        bundle = BundleFactory()
        original_dataset = DatasetFactory()
        # Create inline formset data that keeps the same dataset (no change needed, we just care about args)
        raw = {
            "name": "Bundle",
            "status": BundleStatus.DRAFT,
            "bundled_pages": inline_formset([]),
            "bundled_datasets": inline_formset([{"dataset": original_dataset.id}]),
            "teams": inline_formset([]),
        }
        form = self.form_class(instance=bundle, data=nested_form_data(raw), for_user=self.user)

        with patch("cms.bundles.forms.BundleAPISyncService") as mock_svc_cls:
            self.assertTrue(form.is_valid())
            saved = form.save(commit=True)

            # Assert constructor called with the exact objects we expect
            mock_svc_cls.assert_called_once()
            called_kwargs = mock_svc_cls.call_args.kwargs

            # bundle: the saved bundle instance
            self.assertIs(called_kwargs["bundle"], saved)

            # api_client: the form's cached client instance
            # Accessing ensures the cached_property is initialised on the form instance
            self.assertIsInstance(form.bundle_api_client, BundleAPIClient)
            self.assertIs(called_kwargs["api_client"], form.bundle_api_client)

            # original_datasets: snapshot taken in __init__
            self.assertEqual(called_kwargs["original_datasets"], form.original_datasets)

            # And sync() was invoked once
            mock_svc_cls.return_value.sync.assert_called_once_with()

    def test_save_with_commit_false_does_not_construct_service(self):
        """When commit=False, form should not construct the sync service or call sync()."""
        bundle = BundleFactory()
        raw = {
            "name": "Bundle",
            "status": BundleStatus.DRAFT,
            "bundled_pages": inline_formset([]),
            "bundled_datasets": inline_formset([]),
            "teams": inline_formset([]),
        }
        form = self.form_class(instance=bundle, data=nested_form_data(raw), for_user=self.user)
        with patch("cms.bundles.forms.BundleAPISyncService") as mock_svc_cls:
            self.assertTrue(form.is_valid())
            _saved = form.save(commit=False)
            mock_svc_cls.assert_not_called()


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
        self.ons_patcher = _patch_ons_dataset_api_no_drift()

    def tearDown(self):
        self.patcher.stop()
        self.ons_patcher.stop()

    def raw_form_data_with_dataset(self, dataset: DatasetFactory) -> dict[str, Any]:
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
                "Cannot approve the bundle with 1 dataset not ready to be published:",
                f"Test Dataset (Edition: {dataset.edition}, Status: DRAFT)",
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
                "Cannot approve the bundle with 1 dataset not ready to be published:",
                f"Draft Dataset (Edition: {dataset_2.edition}, Status: DRAFT)",
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
                "Cannot approve the bundle with 2 datasets not ready to be published:",
                f"Draft Dataset 1 (Edition: {dataset_1.edition}, Status: DRAFT)",
                f"Draft Dataset 2 (Edition: {dataset_2.edition}, Status: DRAFT)",
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
            ["Cannot approve the bundle with 1 dataset not ready to be published:", "Bundle content validation failed"],
        )

    def test_dataset_validation_only_runs_when_approving(self):
        """Test that dataset validation only runs when changing status to APPROVED."""
        dataset = DatasetFactory(id=123)
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


@override_settings(DIS_DATASETS_BUNDLE_API_ENABLED=True, BUNDLE_DATASET_METADATA_VALIDATION_ENABLED=True)
class BundleDatasetMetadataValidationTestCase(TestCase):
    """Test cases for dataset metadata drift validation on bundle approval."""

    @classmethod
    def setUpTestData(cls):
        cls.bundle = BundleFactory(name="Test Bundle", bundle_api_bundle_id="test-bundle-123")
        cls.form_class = get_edit_handler(Bundle).get_form_class()
        cls.approver = UserFactory()

    def setUp(self):
        self.client_patcher = patch("cms.bundles.forms.BundleAPIClient")
        mock_client_class = self.client_patcher.start()
        self.mock_client = mock_client_class.return_value
        # Bundle-API contents check is happy by default; we only exercise metadata drift here.
        self.mock_client.get_bundle_contents.return_value = {"items": [], "etag_header": "etag"}

        self.api_metadata: dict[str, dict[str, str]] = {}

        def fake_get(pk: Any = None) -> Any:
            data = self.api_metadata.get(pk, {})
            item = MagicMock()
            item.next = None
            item.title = data.get("title", "")
            item.description = data.get("description", "")
            return item

        self.ons_patcher = patch("cms.bundles.forms.ONSDataset")
        self.mock_ons = self.ons_patcher.start()
        self.mock_ons.objects.get.side_effect = fake_get

    def tearDown(self):
        self.client_patcher.stop()
        self.ons_patcher.stop()

    def _get_approve_form(self, dataset: Dataset) -> Any:
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
        return self.form_class(instance=self.bundle, data=nested_form_data(raw_data), for_user=self.approver)

    def test_metadata_matches_passes(self):
        dataset = DatasetFactory(title="Original Title", description="Original Description")
        self.api_metadata[dataset.namespace] = {"title": dataset.title, "description": dataset.description}

        form = self._get_approve_form(dataset)

        self.assertTrue(form.is_valid(), form.errors)

    def test_title_drift_blocks_approval_and_updates_local_dataset(self):
        dataset = DatasetFactory(title="Original Title", description="Original Description")
        self.api_metadata[dataset.namespace] = {
            "title": "Updated Title",
            "description": dataset.description,
        }

        form = self._get_approve_form(dataset)

        self.assertFalse(form.is_valid())
        non_field_errors = form.non_field_errors()
        self.assertIn(
            "Dataset metadata has changed in the source API since the bundle was last edited or submitted. "
            "The local records have been refreshed - please re-review the changes and reconfirm to approve:",
            non_field_errors,
        )
        self.assertIn(
            "'Original Title': title changed from 'Original Title' to 'Updated Title'",
            non_field_errors,
        )

        dataset.refresh_from_db()
        self.assertEqual(dataset.title, "Updated Title")

    def test_description_drift_blocks_approval_and_updates_local_dataset(self):
        dataset = DatasetFactory(title="Original Title", description="Original Description")
        self.api_metadata[dataset.namespace] = {
            "title": dataset.title,
            "description": "Updated Description",
        }

        form = self._get_approve_form(dataset)

        self.assertFalse(form.is_valid())
        self.assertIn(
            "'Original Title': description has changed",
            form.non_field_errors(),
        )

        dataset.refresh_from_db()
        self.assertEqual(dataset.description, "Updated Description")

    def test_reapproval_after_drift_refresh_succeeds(self):
        """After a first failed approve refreshes the local Dataset, a second approve passes."""
        dataset = DatasetFactory(title="Original Title", description="Original Description")
        self.api_metadata[dataset.namespace] = {
            "title": "Updated Title",
            "description": "Updated Description",
        }

        first = self._get_approve_form(dataset)
        self.assertFalse(first.is_valid())

        # Local Dataset has been refreshed in-place. Re-submitting now finds no drift.
        second = self.form_class(
            instance=self.bundle,
            data=nested_form_data(
                {
                    "name": self.bundle.name,
                    "status": BundleStatus.APPROVED,
                    "bundled_pages": inline_formset([]),
                    "bundled_datasets": inline_formset(
                        [
                            {
                                "id": self.bundle.bundled_datasets.first().id,
                                "dataset": dataset.id,
                                "ORDER": "1",
                            }
                        ],
                        initial=1,
                    ),
                    "teams": inline_formset([]),
                }
            ),
            for_user=self.approver,
        )

        self.assertTrue(second.is_valid(), second.errors)

    def test_api_error_during_metadata_validation_blocks_approval(self):
        """Test that known exceptions during metadata validation are caught and handled gracefully,
        and a validation error message is shown.
        """
        test_exceptions = (
            requests.exceptions.RequestException("API error"),
            ONSDatasetApiQuerySet.does_not_exist_exception("Does not exist"),
            ONSDatasetApiQuerySet.multiple_objects_returned_exception("Multiple objects returned"),
            ValueError("Unexpected value"),
        )

        for test_exception in test_exceptions:
            # Ensure fresh bundle and dataset are used
            self.bundle = BundleFactory()
            dataset = DatasetFactory()
            with self.subTest(exception=test_exception):
                self.mock_ons.objects.get.side_effect = test_exception

                form = self._get_approve_form(dataset)

                self.assertFalse(form.is_valid())
                self.assertIn(
                    f"Could not verify the latest metadata for '{dataset.title}'. Please try again.",
                    form.non_field_errors(),
                )

    def test_other_exceptions_raised_during_metadata_validation_are_not_caught(self):
        """Test that unexpected exceptions during metadata validation are not caught and handled gracefully,
        to avoid masking bugs.
        """
        dataset = DatasetFactory(title="Original Title", description="Original Description")

        class _CustomException(Exception):
            pass

        self.mock_ons.objects.get.side_effect = _CustomException("Unexpected error")

        form = self._get_approve_form(dataset)

        with self.assertRaises(_CustomException) as cm:
            form.is_valid()
        self.assertEqual(str(cm.exception), "Unexpected error")


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
