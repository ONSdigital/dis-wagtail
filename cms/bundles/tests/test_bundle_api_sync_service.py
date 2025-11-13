# pylint: disable=too-many-lines

from unittest.mock import Mock, patch

from django.core.exceptions import ValidationError
from django.test import TestCase, override_settings

from cms.bundles.bundle_api_sync_service import BundleAPISyncService
from cms.bundles.clients.api import BundleAPIClient, BundleAPIClientError, BundleAPIClientError404
from cms.bundles.enums import BundleStatus
from cms.bundles.tests.factories import BundleDatasetFactory, BundleFactory
from cms.bundles.utils import BundleAPIBundleMetadata, build_content_item_for_dataset
from cms.datasets.tests.factories import DatasetFactory


@override_settings(DIS_DATASETS_BUNDLE_API_ENABLED=True)
class BundleAPISyncServiceTests(TestCase):
    """Tests for BundleAPISyncService."""

    def setUp(self):
        self.bundle = BundleFactory(name="Test Bundle", status=BundleStatus.DRAFT)
        self.api_client = Mock(spec=BundleAPIClient)
        self.original_datasets: set = set()

    def _create_service(self, bundle=None, api_client=None, original_datasets=None):
        """Helper to create a BundleAPISyncService instance."""
        return BundleAPISyncService(
            bundle=bundle or self.bundle,
            api_client=api_client or self.api_client,
            original_datasets=original_datasets or self.original_datasets,
        )

    def _mock_api_bundle(self, state="DRAFT", title="Test Bundle", etag="etag-123", **kwargs):
        """Helper to create a standard API bundle response."""
        return {
            "state": state,
            "title": title,
            "etag_header": etag,
            "bundle_type": kwargs.get("bundle_type", "MANUAL"),
            "managed_by": kwargs.get("managed_by", "WAGTAIL"),
            "preview_teams": kwargs.get("preview_teams", []),
            "scheduled_at": kwargs.get("scheduled_at"),
        }

    def _mock_api_content_item(self, *, content_id, dataset_id, edition_id, version_id, etag="etag-123"):
        """Helper to create a standard API content item."""
        return {
            "etag_header": etag,
            "id": content_id,
            "metadata": {
                "dataset_id": dataset_id,
                "edition_id": edition_id,
                "version_id": version_id,
            },
        }

    def _setup_bundle_with_api_id(self, bundle_id="bundle-123", etag="etag-123"):
        """Helper to set up bundle with API ID and ETag."""
        self.bundle.bundle_api_bundle_id = bundle_id
        self.bundle.bundle_api_etag = etag
        self.bundle.save()

    def test_metadata_comparison_returns_true_when_cms_matches_api(self):
        """Test metadata_is_in_sync returns True when CMS and API metadata are identical."""
        # Given
        self._setup_bundle_with_api_id()
        service = self._create_service()

        self.api_client.get_bundle.return_value = self._mock_api_bundle(
            state="DRAFT",
            title="Test Bundle",
            etag="etag-123",
            bundle_type="MANUAL",
            managed_by="WAGTAIL",
            preview_teams=[],
            scheduled_at=None,
        )

        # When/Then
        self.assertTrue(service.metadata_is_in_sync)

    def test_metadata_comparison_returns_false_when_cms_differs_from_api(self):
        """Test metadata_is_in_sync returns False when any CMS metadata field differs from API."""
        # Given
        self._setup_bundle_with_api_id()
        service = self._create_service()

        test_cases = [
            ("title", {"title": "Different Title"}),
            (
                "bundle_type",
                {
                    "bundle_type": "SCHEDULED",
                },
            ),
            ("state", {"state": "PUBLISHED"}),
            ("preview_teams", {"preview_teams": ["team1"]}),
            ("scheduled_at", {"scheduled_at": "2025-12-01T00:00:00Z"}),
        ]

        for field_name, override_kwargs in test_cases:
            with self.subTest(field=field_name):
                # When
                self.api_client.get_bundle.return_value = self._mock_api_bundle(**override_kwargs)
                result = service.metadata_is_in_sync

                # Then
                self.assertFalse(result, f"Expected metadata_is_in_sync to be False for field '{field_name}'")

    def test_create_bundle_when_cms_has_datasets_but_no_api_bundle(self):
        """Test sync creates a new API bundle when CMS bundle has datasets but no remote bundle exists."""
        # Given
        dataset = DatasetFactory(namespace="test-ns", edition="2024", version=1)
        BundleDatasetFactory(parent=self.bundle, dataset=dataset)

        self.bundle.bundle_api_bundle_id = ""
        service = self._create_service()

        self.api_client.create_bundle.return_value = {
            "id": "new-bundle-123",
            "etag_header": "new-etag",
            "state": "DRAFT",
        }
        self.api_client.get_bundle.return_value = self._mock_api_bundle(etag="new-etag")
        self.api_client.get_bundle_contents.return_value = {"items": []}
        self.api_client.add_content_to_bundle.return_value = self._mock_api_content_item(
            content_id="content-123",
            dataset_id="test-ns",
            edition_id="2024",
            version_id=1,
            etag="content-etag",
        )

        # When
        service.sync()

        # Then
        self.api_client.create_bundle.assert_called_once()
        self.bundle.refresh_from_db()
        self.assertEqual(self.bundle.bundle_api_bundle_id, "new-bundle-123")
        self.assertIn(self.bundle.bundle_api_etag, ["new-etag", "content-etag"])

    def test_create_bundle_skipped_when_cms_has_no_datasets_and_no_api_bundle(self):
        """Test sync skips bundle creation when CMS bundle has no datasets and no remote bundle exists."""
        # Given
        self.bundle.bundle_api_bundle_id = ""
        service = self._create_service()

        # When
        service.sync()

        # Then
        self.api_client.create_bundle.assert_not_called()
        self.api_client.get_bundle.assert_not_called()

    def test_creates_in_review_bundle_as_draft_then_syncs_metadata(self):
        """Test sync creates IN_REVIEW bundles as DRAFT in API, then syncs metadata to update state."""
        # Given
        dataset = DatasetFactory(namespace="test-ns", edition="2024", version=1)
        BundleDatasetFactory(parent=self.bundle, dataset=dataset)

        # Local bundle is IN_REVIEW but has no remote counterpart yet
        self.bundle.status = BundleStatus.IN_REVIEW
        self.bundle.bundle_api_bundle_id = ""
        self.bundle.save()

        service = self._create_service()

        self.api_client.create_bundle.return_value = {
            "id": "new-bundle-123",
            "etag_header": "create-etag",
            "state": "DRAFT",
        }
        self.api_client.get_bundle.return_value = self._mock_api_bundle(etag="create-etag")
        self.api_client.get_bundle_contents.return_value = {"items": []}
        self.api_client.add_content_to_bundle.return_value = self._mock_api_content_item(
            content_id="content-123",
            dataset_id="test-ns",
            edition_id="2024",
            version_id=1,
            etag="content-etag",
        )
        self.api_client.update_bundle.return_value = {"etag_header": "metadata-sync-etag"}

        # When
        service.sync()

        # Then
        # Assert create_bundle called with a DRAFT state
        self.api_client.create_bundle.assert_called_once()
        args, kwargs = self.api_client.create_bundle.call_args
        created_bundle_data = kwargs.get("bundle_data") or args[0]
        self.assertEqual(created_bundle_data.state, BundleStatus.DRAFT)

        # Assert update_bundle called with IN_REVIEW state
        self.api_client.update_bundle.assert_called_once()
        _, update_kwargs = self.api_client.update_bundle.call_args
        synced_bundle_data = update_kwargs["bundle_data"]
        self.assertEqual(synced_bundle_data.state, BundleStatus.IN_REVIEW)

        # Assert update_state was not called
        self.api_client.update_bundle_state.assert_not_called()

        # Verify final local state
        self.bundle.refresh_from_db()
        self.assertEqual(self.bundle.bundle_api_bundle_id, "new-bundle-123")
        self.assertEqual(self.bundle.status, BundleStatus.IN_REVIEW)  # Local status unchanged

    def test_etag_sync_behavior(self):
        """Test ETag is updated when stale and unchanged when current."""
        test_cases = [
            ("stale", "old-etag", "new-etag", True),
            ("current", "same-etag", "same-etag", False),
        ]

        for case_name, local_etag, api_etag, should_save in test_cases:
            with self.subTest(case=case_name):
                # Reset bundle state for each iteration
                self.bundle.refresh_from_db()
                # Given
                self.bundle.bundle_api_bundle_id = "bundle-123"
                self.bundle.bundle_api_etag = local_etag
                self.bundle.status = BundleStatus.APPROVED
                self.bundle.save()

                service = self._create_service()
                self.api_client.get_bundle.return_value = self._mock_api_bundle(etag=api_etag, state="APPROVED")

                # When
                with patch.object(self.bundle, "save", wraps=self.bundle.save) as mock_save:
                    service.sync()

                    # Then
                    if should_save:
                        mock_save.assert_called()
                    else:
                        mock_save.assert_not_called()

                # Then
                self.bundle.refresh_from_db()
                self.assertEqual(self.bundle.bundle_api_etag, api_etag)

                # Reset mocks for next iteration
                self.api_client.reset_mock()

    def test_state_sync_for_immutable_bundles(self):
        """Test sync handles state for APPROVED/PUBLISHED bundles based on API state."""
        test_cases = [
            (BundleStatus.APPROVED, "DRAFT", True),  # API is stale - sync state
            (BundleStatus.APPROVED, "APPROVED", False),  # API is current - skip sync
            (BundleStatus.PUBLISHED, "DRAFT", True),  # API is stale - sync state
            (BundleStatus.PUBLISHED, "PUBLISHED", False),  # API is current - skip sync
        ]

        for local_status, api_state, should_sync_state in test_cases:
            with self.subTest(local=local_status, api=api_state, should_sync=should_sync_state):
                # Reset bundle state for each iteration
                self.bundle.refresh_from_db()
                # Given
                self.bundle.status = local_status
                self._setup_bundle_with_api_id()

                service = self._create_service()

                self.api_client.get_bundle.return_value = self._mock_api_bundle(etag="etag-123", state=api_state)
                self.api_client.update_bundle_state.return_value = {
                    "etag_header": "new-etag",
                }

                # When
                service.sync()

                # Then
                if should_sync_state:
                    self.api_client.update_bundle_state.assert_called_once_with(
                        "bundle-123", state=local_status, etag="etag-123"
                    )
                    self.bundle.refresh_from_db()
                    self.assertEqual(self.bundle.bundle_api_etag, "new-etag")
                else:
                    self.api_client.update_bundle_state.assert_not_called()

                # Verify no metadata update for immutable statuses
                self.api_client.update_bundle.assert_not_called()
                self.api_client.get_bundle_contents.assert_not_called()

                # Reset mocks for next iteration
                self.api_client.reset_mock()

    def test_metadata_sync_behavior(self):
        """Test sync syncs metadata only when CMS differs from API."""
        test_cases = [
            ("stale", "Different Title", True),
            ("in_sync", "Test Bundle", False),
        ]

        for case_name, api_title, should_sync in test_cases:
            with self.subTest(case=case_name):
                # Given
                dataset = DatasetFactory(namespace=f"test-ns-{case_name}", edition="2024", version=1)
                bundled_dataset = BundleDatasetFactory(
                    parent=self.bundle, dataset=dataset, bundle_api_content_id="content-123"
                )
                self._setup_bundle_with_api_id()

                service = self._create_service()

                self.api_client.get_bundle.return_value = self._mock_api_bundle(
                    etag="etag-123", state="DRAFT", title=api_title
                )
                self.api_client.update_bundle.return_value = {"etag_header": "new-etag"}

                # When
                service.sync()

                # Then
                if should_sync:
                    self.api_client.update_bundle.assert_called_once_with(
                        bundle_id="bundle-123",
                        bundle_data=BundleAPIBundleMetadata.from_bundle(self.bundle),
                        etag="etag-123",
                    )
                else:
                    self.api_client.update_bundle.assert_not_called()

                # Clean up for next iteration
                bundled_dataset.delete()
                dataset.delete()
                self.api_client.reset_mock()

    def test_deletes_remote_bundle_when_any_step_fails_after_creation(self):
        """Test sync deletes newly created remote bundle if any subsequent step fails."""
        # Given
        BundleDatasetFactory(parent=self.bundle)

        self.bundle.bundle_api_bundle_id = ""
        service = self._create_service()

        self.api_client.create_bundle.return_value = {
            "id": "new-bundle-123",
            "etag_header": "new-etag",
        }
        self.api_client.get_bundle.side_effect = [{"etag_header": "new-etag"}]
        self.api_client.get_bundle_contents.side_effect = BundleAPIClientError("API Error")
        self.api_client.delete_bundle.return_value = None

        # When/Then
        with self.assertRaises(ValidationError):
            service.sync()

        self.api_client.delete_bundle.assert_called_once_with("new-bundle-123")

    def test_deletes_remote_bundle_when_no_datasets_remain(self):
        """Test sync deletes remote bundle when CMS bundle has no datasets."""
        # Given
        self._setup_bundle_with_api_id()

        # Bundle has no datasets
        self.assertEqual(self.bundle.bundled_datasets.count(), 0)

        service = self._create_service()

        self.api_client.get_bundle.return_value = self._mock_api_bundle()
        self.api_client.delete_bundle.return_value = None

        # When
        service.sync()

        # Then
        self.api_client.delete_bundle.assert_called_once_with("bundle-123")

        # Verify local IDs are cleared
        self.bundle.refresh_from_db()
        self.assertEqual(self.bundle.bundle_api_bundle_id, "")
        self.assertEqual(self.bundle.bundle_api_etag, "")

    def test_content_sync_skipped_when_no_drift_and_etag_current(self):
        """Test sync skips content reconciliation when datasets unchanged and ETag is current."""
        # Given
        dataset = DatasetFactory(namespace="test-ns", edition="2024", version=1)
        bundled_dataset = BundleDatasetFactory(parent=self.bundle, dataset=dataset, bundle_api_content_id="content-123")

        self.bundle.bundle_api_bundle_id = "bundle-123"
        self.bundle.bundle_api_etag = "current-etag"
        self.bundle.save()

        # Original datasets match current - no drift
        service = self._create_service(original_datasets={bundled_dataset})

        self.api_client.get_bundle.return_value = self._mock_api_bundle(etag="current-etag")

        # When
        service.sync()

        # Then
        self.api_client.get_bundle_contents.assert_not_called()
        self.api_client.add_content_to_bundle.assert_not_called()
        self.api_client.delete_content_from_bundle.assert_not_called()

    def test_content_sync_performed_when_etag_stale_even_without_drift(self):
        """Test sync reconciles content when ETag is stale even if datasets are unchanged."""
        # Given
        dataset = DatasetFactory(namespace="test-ns", edition="2024", version=1)
        bundled_dataset = BundleDatasetFactory(parent=self.bundle, dataset=dataset, bundle_api_content_id="content-123")

        self.bundle.bundle_api_bundle_id = "bundle-123"
        self.bundle.bundle_api_etag = "old-etag"
        self.bundle.save()

        # Original datasets match current - no drift
        service = self._create_service(original_datasets={bundled_dataset})

        self.api_client.get_bundle.return_value = self._mock_api_bundle(etag="new-etag")
        self.api_client.get_bundle_contents.return_value = {
            "items": [
                self._mock_api_content_item(
                    content_id="content-123",
                    dataset_id="test-ns",
                    edition_id="2024",
                    version_id=1,
                )
            ]
        }

        # When
        service.sync()

        # Then
        # Should fetch contents for reconciliation despite no local drift
        self.api_client.get_bundle_contents.assert_called_once_with("bundle-123")

        # Verify ETag was refreshed
        self.bundle.refresh_from_db()
        self.assertEqual(self.bundle.bundle_api_etag, "new-etag")

    def test_content_sync_adds_new_datasets_to_api(self):
        """Test sync adds datasets that exist in CMS but not in API."""
        # Given
        dataset = DatasetFactory(namespace="test-ns", edition="2024", version=1)
        bundled_dataset = BundleDatasetFactory(parent=self.bundle, dataset=dataset, bundle_api_content_id="")

        self._setup_bundle_with_api_id()

        service = self._create_service()

        self.api_client.get_bundle.return_value = self._mock_api_bundle()
        self.api_client.get_bundle_contents.return_value = {"items": []}
        self.api_client.add_content_to_bundle.return_value = self._mock_api_content_item(
            content_id="new-content-123",
            dataset_id="test-ns",
            edition_id="2024",
            version_id=1,
            etag="new-etag",
        )

        # When
        service.sync()

        # Then
        self.api_client.add_content_to_bundle.assert_called_once()
        bundled_dataset.refresh_from_db()
        self.assertEqual(bundled_dataset.bundle_api_content_id, "new-content-123")

    def test_content_sync_deletes_removed_datasets_from_api(self):
        """Test sync deletes datasets that were removed from CMS or does not exist locally but exist in API."""
        # Given
        dataset1 = DatasetFactory(namespace="test-ns", edition="2024", version=1)
        dataset2 = DatasetFactory(namespace="other-ns", edition="2024", version=2)

        bundled_dataset1 = BundleDatasetFactory(
            parent=self.bundle, dataset=dataset1, bundle_api_content_id="content-123"
        )
        BundleDatasetFactory(parent=self.bundle, dataset=dataset2, bundle_api_content_id="content-456")

        self._setup_bundle_with_api_id()

        original_datasets = set(self.bundle.bundled_datasets.all())

        # Remove only the first dataset from the bundle - keep the second one
        bundled_dataset1.delete()

        self.assertEqual(self.bundle.bundled_datasets.count(), 1)

        # But original_datasets should still contain both items
        self.assertEqual(len(original_datasets), 2)

        service = self._create_service(original_datasets=original_datasets)

        self.api_client.get_bundle.return_value = self._mock_api_bundle()
        # API still has both content items, but CMS only has the second one
        self.api_client.get_bundle_contents.return_value = {
            "items": [
                self._mock_api_content_item(
                    content_id="content-123",
                    dataset_id="test-ns",
                    edition_id="2024",
                    version_id=1,
                ),
                self._mock_api_content_item(
                    content_id="content-456",
                    dataset_id="other-ns",
                    edition_id="2024",
                    version_id=2,
                ),
            ]
        }
        self.api_client.delete_content_from_bundle.return_value = {"etag_header": "new-etag"}

        # When
        service.sync()

        # Then
        self.api_client.delete_content_from_bundle.assert_called_once_with(
            bundle_id="bundle-123", content_id="content-123"
        )

    def test_content_sync_backfills_missing_content_ids(self):
        """Test sync backfills content IDs for datasets already in API but missing local ID."""
        # Given
        dataset = DatasetFactory(namespace="test-ns", edition="2024", version="1")
        bundled_dataset = BundleDatasetFactory(
            parent=self.bundle,
            dataset=dataset,
            bundle_api_content_id="",
        )

        self.bundle.bundle_api_bundle_id = "bundle-123"
        self.bundle.save()

        service = self._create_service()

        self.api_client.get_bundle.return_value = self._mock_api_bundle()
        self.api_client.get_bundle_contents.return_value = {
            "items": [
                self._mock_api_content_item(
                    content_id="existing-content-123",
                    dataset_id="test-ns",
                    edition_id="2024",
                    version_id="1",
                )
            ]
        }

        # When
        service.sync()

        # Then
        # Verify content ID was backfilled
        bundled_dataset.refresh_from_db()
        self.assertEqual(bundled_dataset.bundle_api_content_id, "existing-content-123")
        self.api_client.add_content_to_bundle.assert_not_called()

    def test_content_sync_handles_add_delete_and_backfill_simultaneously(self):
        """Test sync handles adding, deleting, and backfilling datasets in a single sync operation."""
        # Given
        dataset1 = DatasetFactory(namespace="ns1", edition="2024", version=1)
        BundleDatasetFactory(parent=self.bundle, dataset=dataset1, bundle_api_content_id="content-1")

        dataset2 = DatasetFactory(namespace="ns2", edition="2024", version=2)
        BundleDatasetFactory(parent=self.bundle, dataset=dataset2, bundle_api_content_id="")

        dataset3 = DatasetFactory(namespace="ns3", edition="2024", version=3)
        bundled_dataset3 = BundleDatasetFactory(parent=self.bundle, dataset=dataset3, bundle_api_content_id="")

        dataset4 = DatasetFactory(namespace="ns4", edition="2024", version=4)
        removed_dataset = BundleDatasetFactory(parent=self.bundle, dataset=dataset4, bundle_api_content_id="content-4")

        self.bundle.bundle_api_bundle_id = "bundle-123"
        self.bundle.bundle_api_etag = "old-etag"
        self.bundle.save()

        original_datasets = set(self.bundle.bundled_datasets.all())
        removed_dataset.delete()

        service = self._create_service(original_datasets=original_datasets)

        self.api_client.get_bundle.return_value = self._mock_api_bundle(etag="new-etag")
        self.api_client.get_bundle_contents.return_value = {
            "items": [
                self._mock_api_content_item(content_id="content-1", dataset_id="ns1", edition_id="2024", version_id=1),
                self._mock_api_content_item(content_id="content-3", dataset_id="ns3", edition_id="2024", version_id=3),
                self._mock_api_content_item(content_id="content-4", dataset_id="ns4", edition_id="2024", version_id=4),
            ]
        }

        self.api_client.add_content_to_bundle.return_value = self._mock_api_content_item(
            content_id="content-2",
            dataset_id="ns2",
            edition_id="2024",
            version_id=2,
            etag="add-etag",
        )

        self.api_client.delete_content_from_bundle.return_value = {"etag_header": "delete-etag"}

        # When
        service.sync()

        # Then
        bundled_dataset3.refresh_from_db()
        self.assertEqual(bundled_dataset3.bundle_api_content_id, "content-3")

        self.api_client.add_content_to_bundle.assert_called_once_with(
            bundle_id="bundle-123",
            content_item=build_content_item_for_dataset(
                dataset=dataset2,
            ),
        )

        self.api_client.delete_content_from_bundle.assert_called_once_with(
            bundle_id="bundle-123", content_id="content-4"
        )

        self.bundle.refresh_from_db()
        self.assertEqual(self.bundle.bundle_api_etag, "delete-etag")

    def test_raises_validation_error_when_adding_content_fails(self):
        """Test sync raises ValidationError when adding content to API fails."""
        # Given
        dataset = DatasetFactory(namespace="test-ns", edition="2024", version="1")
        BundleDatasetFactory(parent=self.bundle, dataset=dataset, bundle_api_content_id="")

        self._setup_bundle_with_api_id()

        service = self._create_service()

        self.api_client.get_bundle.return_value = self._mock_api_bundle()
        self.api_client.get_bundle_contents.return_value = {"items": []}
        self.api_client.add_content_to_bundle.side_effect = BundleAPIClientError("API Error")

        # When/Then
        with self.assertRaises(ValidationError) as context:
            service.sync()

        self.assertIn("Failed to add dataset to bundle", str(context.exception))

    def test_raises_validation_error_when_content_id_not_returned_by_api(self):
        """Test sync raises ValidationError when API doesn't return content ID after adding dataset."""
        # Given
        dataset = DatasetFactory(namespace="test-ns", edition="2024", version="1")
        BundleDatasetFactory(parent=self.bundle, dataset=dataset, bundle_api_content_id="")

        self._setup_bundle_with_api_id()

        service = self._create_service()

        self.api_client.get_bundle.return_value = self._mock_api_bundle()
        self.api_client.get_bundle_contents.return_value = {"items": []}
        # Return response without matching metadata (no content ID for our dataset)
        self.api_client.add_content_to_bundle.return_value = self._mock_api_content_item(
            content_id="wrong-content-id",
            dataset_id="different-ns",
            edition_id="2024",
            version_id="1",
            etag="new-etag",
        )

        # When/Then
        with self.assertRaises(ValidationError) as context:
            service.sync()

        self.assertIn(
            f"Failed to add dataset to bundle in Bundle API. "
            f"Bundle API did not return a content ID for the added dataset - {dataset}",
            str(context.exception),
        )

    def test_raises_validation_error_when_deleting_content_fails(self):
        """Test sync raises ValidationError when deleting content from API fails."""
        # Given
        dataset1 = DatasetFactory(namespace="test-ns", edition="2024", version=1)
        dataset2 = DatasetFactory(namespace="keep-ns", edition="2024", version=2)

        bundled_dataset1 = BundleDatasetFactory(
            parent=self.bundle, dataset=dataset1, bundle_api_content_id="content-to-delete"
        )
        BundleDatasetFactory(parent=self.bundle, dataset=dataset2, bundle_api_content_id="content-to-keep")

        self.bundle.bundle_api_bundle_id = "bundle-123"
        self.bundle.bundle_api_etag = "old-etag"
        self.bundle.save()

        original_datasets = set(self.bundle.bundled_datasets.all())
        bundled_dataset1.delete()

        service = self._create_service(original_datasets=original_datasets)

        self.api_client.get_bundle.return_value = self._mock_api_bundle(etag="new-etag")
        # API still has both contents - one should be deleted, one should remain
        self.api_client.get_bundle_contents.return_value = {
            "items": [
                self._mock_api_content_item(
                    content_id="content-to-delete",
                    dataset_id="test-ns",
                    edition_id="2024",
                    version_id=1,
                ),
                self._mock_api_content_item(
                    content_id="content-to-keep",
                    dataset_id="keep-ns",
                    edition_id="2024",
                    version_id=2,
                ),
            ]
        }
        self.api_client.delete_content_from_bundle.side_effect = BundleAPIClientError("API Error")

        # When/Then
        with self.assertRaises(ValidationError) as context:
            service.sync()

        self.assertIn("Failed to delete dataset from bundle", str(context.exception))

    def test_raises_validation_error_on_state_sync_failure(self):
        """Test sync raises ValidationError when state sync fails for immutable bundles."""
        # Given
        self.bundle.status = BundleStatus.APPROVED
        self._setup_bundle_with_api_id()

        service = self._create_service()

        self.api_client.get_bundle.return_value = self._mock_api_bundle(state="DRAFT", etag="etag-123")
        self.api_client.update_bundle_state.side_effect = BundleAPIClientError("API Error")

        # When/Then
        with self.assertRaises(ValidationError) as context:
            service.sync()

        self.assertIn("Failed to sync bundle state", str(context.exception))

    def test_sync_wraps_non_validation_errors(self):
        """Test sync wraps non-ValidationError exceptions in ValidationError."""
        # Given
        dataset = DatasetFactory(namespace="test-ns", edition="2024", version=1)
        BundleDatasetFactory(parent=self.bundle, dataset=dataset, bundle_api_content_id="content-123")

        self.bundle.bundle_api_bundle_id = "bundle-123"
        self.bundle.save()

        service = self._create_service()

        self.api_client.get_bundle.return_value = self._mock_api_bundle(etag="etag-123")
        self.api_client.get_bundle_contents.side_effect = RuntimeError("Unexpected error")

        # When/Then
        with self.assertRaises(ValidationError) as context:
            service.sync()

        self.assertIn("Failed to sync bundle with Bundle API", str(context.exception))

    def test_sync_reraises_validation_errors_without_wrapping(self):
        """Test sync re-raises ValidationError without wrapping it."""
        # Given
        dataset = DatasetFactory(namespace="test-ns", edition="2024", version=1)
        BundleDatasetFactory(parent=self.bundle, dataset=dataset, bundle_api_content_id="")  # No content ID = drift

        self._setup_bundle_with_api_id()

        service = self._create_service()

        self.api_client.get_bundle.return_value = self._mock_api_bundle()

        # Make get_bundle_contents raise a ValidationError directly
        original_error = ValidationError("Original validation error")
        self.api_client.get_bundle_contents.side_effect = original_error

        # When/Then
        # Should re-raise the same ValidationError, not wrap it
        with self.assertRaises(ValidationError) as context:
            service.sync()

        self.assertIn("Original validation error", str(context.exception))

    def test_raises_error_when_metadata_update_fails(self):
        """Test sync raises ValidationError when metadata update fails."""
        # Given
        dataset = DatasetFactory(namespace="test-ns", edition="2024", version=1)
        BundleDatasetFactory(parent=self.bundle, dataset=dataset, bundle_api_content_id="content-123")

        self._setup_bundle_with_api_id()

        service = self._create_service()

        self.api_client.get_bundle.return_value = self._mock_api_bundle(title="Different Title")
        self.api_client.get_bundle_contents.return_value = {
            "items": [
                self._mock_api_content_item(
                    content_id="content-123",
                    dataset_id="test-ns",
                    edition_id="2024",
                    version_id=1,
                )
            ]
        }

        # Make update_bundle fail
        self.api_client.update_bundle.side_effect = BundleAPIClientError("API Error")

        # When/Then
        with self.assertRaises(ValidationError) as context:
            service.sync()

        self.assertIn("Failed to sync bundle with Bundle API", str(context.exception))

    def test_deletes_remote_bundle_on_metadata_sync_failure_after_creation(self):
        """Test sync deletes remote bundle if metadata sync fails after bundle creation."""
        # Given
        dataset = DatasetFactory(namespace="test-ns", edition="2024", version=1)
        BundleDatasetFactory(parent=self.bundle, dataset=dataset)

        self.bundle.bundle_api_bundle_id = ""
        service = self._create_service()

        self.api_client.create_bundle.return_value = {
            "id": "new-bundle-123",
            "etag_header": "new-etag",
            "state": "DRAFT",
        }
        # Return different title to trigger metadata sync
        self.api_client.get_bundle.return_value = self._mock_api_bundle(title="Different Title", etag="new-etag")
        self.api_client.get_bundle_contents.return_value = {"items": []}
        self.api_client.add_content_to_bundle.return_value = self._mock_api_content_item(
            content_id="content-123",
            dataset_id="test-ns",
            edition_id="2024",
            version_id=1,
            etag="content-etag",
        )
        # Metadata sync fails
        self.api_client.update_bundle.side_effect = BundleAPIClientError("Metadata sync failed")
        self.api_client.delete_bundle.return_value = None

        # When/Then
        with self.assertRaises(ValidationError):
            service.sync()

        self.api_client.delete_bundle.assert_called_once_with("new-bundle-123")

    def test_handles_save_failure_after_bundle_creation(self):
        """Test sync handles exception when saving bundle metadata after API creation."""
        # Given
        dataset = DatasetFactory(namespace="test-ns", edition="2024", version=1)
        BundleDatasetFactory(parent=self.bundle, dataset=dataset)

        self.bundle.bundle_api_bundle_id = ""
        service = self._create_service()

        self.api_client.create_bundle.return_value = {
            "id": "new-bundle-123",
            "etag_header": "new-etag",
        }
        self.api_client.delete_bundle.return_value = None

        # Use side_effect to fail on first save attempt
        self.bundle.save = Mock(side_effect=[RuntimeError("Database error during save"), None])

        # When/Then
        with self.assertRaises(ValidationError) as context:
            service.sync()

        self.assertIn("Failed to save bundle API metadata", str(context.exception))
        self.api_client.delete_bundle.assert_called_once_with("new-bundle-123")

    def test_sync_wraps_non_validation_error_from_cleanup_delete(self):
        """Test sync wraps non-ValidationError from cleanup delete (covers _delete_api_bundle)."""
        # Given
        dataset = DatasetFactory(namespace="test-ns", edition="2024", version=1)
        BundleDatasetFactory(parent=self.bundle, dataset=dataset)

        self.bundle.bundle_api_bundle_id = ""
        service = self._create_service()

        self.api_client.create_bundle.return_value = {
            "id": "new-bundle-123",
            "etag_header": "new-etag",
        }

        # First save fails, triggering cleanup delete
        self.bundle.save = Mock(side_effect=RuntimeError("Save failed"))

        # Delete raises BundleAPIClientError (not ValidationError) - should be wrapped
        self.api_client.delete_bundle.side_effect = BundleAPIClientError("Network error during cleanup")

        # When/Then
        with self.assertRaises(ValidationError) as context:
            service.sync()

        self.assertIn("Failed to delete bundle from Bundle API", str(context.exception))
        self.api_client.delete_bundle.assert_called_once_with("new-bundle-123")

    def test_handles_404_when_deleting_empty_bundle(self):
        """Test sync handles 404 gracefully when deleting non-existent bundle."""
        # Given
        self._setup_bundle_with_api_id()

        # No datasets - should trigger deletion
        self.assertEqual(self.bundle.bundled_datasets.count(), 0)

        service = self._create_service()

        self.api_client.get_bundle.return_value = self._mock_api_bundle()
        # Bundle already deleted (404)
        self.api_client.delete_bundle.side_effect = BundleAPIClientError404("Not found")

        # When
        service.sync()

        # Then
        self.api_client.delete_bundle.assert_called_once_with("bundle-123")
        # Bundle IDs should be cleared even though 404
        self.bundle.refresh_from_db()
        self.assertEqual(self.bundle.bundle_api_bundle_id, "")
        self.assertEqual(self.bundle.bundle_api_etag, "")

    def test_sync_reraises_validation_error_from_delete_operation(self):
        """Test sync re-raises ValidationError from delete without wrapping (covers _delete_api_bundle)."""
        # Given
        dataset = DatasetFactory(namespace="test-ns", edition="2024", version=1)
        BundleDatasetFactory(parent=self.bundle, dataset=dataset)

        self.bundle.bundle_api_bundle_id = ""
        service = self._create_service()

        self.api_client.create_bundle.return_value = {
            "id": "new-bundle-123",
            "etag_header": "new-etag",
        }

        # First save fails, triggering cleanup
        original_validation_error = ValidationError("Validation error from delete")
        self.bundle.save = Mock(side_effect=RuntimeError("Save failed"))
        self.api_client.delete_bundle.side_effect = original_validation_error

        # When/Then
        with self.assertRaises(ValidationError) as context:
            service.sync()

        # Should re-raise the original ValidationError, not wrap it
        self.assertEqual(context.exception, original_validation_error)

    def test_syncs_content_even_when_some_api_items_are_malformed(self):
        """Test sync raises ValidationError when API create response is missing 'id' field."""
        # Given
        dataset = DatasetFactory(namespace="test-ns", edition="2024", version=1)
        BundleDatasetFactory(parent=self.bundle, dataset=dataset)

        self.bundle.bundle_api_bundle_id = ""
        service = self._create_service()

        self.api_client.create_bundle.return_value = {
            "etag_header": "new-etag",
            # Missing 'id' key - will trigger KeyError
        }

        # When/Then
        with self.assertRaises(ValidationError) as context:
            service.sync()

        self.assertIn("Failed to create bundle in Bundle API", str(context.exception))

    def test_handles_missing_keys_in_get_bundle_contents_response(self) -> None:
        """Test sync handles missing keys in get_bundle_contents response gracefully."""
        # Given
        dataset = DatasetFactory(namespace="dataset-to-add", edition="2024", version=1)
        BundleDatasetFactory(parent=self.bundle, dataset=dataset)

        self._setup_bundle_with_api_id()

        service = self._create_service()

        self.api_client.get_bundle.return_value = self._mock_api_bundle()
        # API returns content items with various missing required keys
        # These malformed items should be skipped during reconciliation
        self.api_client.get_bundle_contents.return_value = {
            "items": [
                {
                    "id": "content-123",
                    "metadata": {
                        "dataset_id": "test-ns",
                        "edition_id": "2024",
                        # missing 'version_id' key - should be skipped
                    },
                },
                {
                    "id": "content-456",
                    "metadata": {
                        "dataset_id": "test-ns",
                        # missing 'edition_id' key - should be skipped
                        "version_id": 2,
                    },
                },
                {
                    "id": "content-789",
                    "metadata": {
                        # missing 'dataset_id' key - should be skipped
                        "edition_id": "2024",
                        "version_id": 1,
                    },
                },
                {
                    # missing 'id' key - should be skipped
                    "metadata": {
                        "dataset_id": "test-ns",
                        "edition_id": "2024",
                        "version_id": 1,
                    }
                },
                {
                    "id": "content-000",
                    # missing 'metadata' key - should be skipped
                },
                {
                    "id": "content-to-remove",
                    "metadata": {
                        "dataset_id": "nonexistent-ns",
                        "edition_id": "2024",
                        "version_id": 1,
                    },
                },
            ]
        }

        self.api_client.add_content_to_bundle.return_value = {
            "etag_header": "new-etag-add",
            "id": "new-content-id",
            "metadata": {"dataset_id": "dataset-to-add", "edition_id": "2024", "version_id": 1},
        }
        self.api_client.delete_content_from_bundle.return_value = {"etag_header": "new-etag-delete"}

        # When
        service.sync()

        # Then
        # Malformed items are ignored, valid item is deleted, missing dataset is added
        self.api_client.delete_content_from_bundle.assert_called_once_with(
            bundle_id="bundle-123", content_id="content-to-remove"
        )

        self.api_client.add_content_to_bundle.assert_called_once_with(
            bundle_id="bundle-123",
            content_item=build_content_item_for_dataset(
                dataset=dataset,
            ),
        )


@override_settings(DIS_DATASETS_BUNDLE_API_ENABLED=False)
class BundleAPISyncServiceDisabledTests(TestCase):
    """Tests for BundleAPISyncService when Bundle API is disabled."""

    def test_sync_does_nothing_when_api_disabled(self):
        """Test sync does nothing when Bundle API is disabled."""
        # Given
        bundle = BundleFactory(name="Test Bundle", status=BundleStatus.DRAFT, bundle_api_bundle_id="abc")

        api_client = Mock(spec=BundleAPIClient)
        service = BundleAPISyncService(
            bundle=bundle,
            api_client=api_client,
            original_datasets=set(),
        )

        # When
        service.sync()

        # Then
        # No API calls should be made
        api_client.create_bundle.assert_not_called()
        api_client.get_bundle.assert_not_called()
