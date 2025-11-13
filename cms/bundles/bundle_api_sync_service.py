import logging
from collections.abc import Iterable
from dataclasses import dataclass, replace
from functools import cached_property
from typing import TYPE_CHECKING

from django.core.exceptions import ValidationError

from cms.bundles.clients.api import (
    BundleAPIClient,
    BundleAPIClientError,
    BundleAPIClientError404,
)
from cms.bundles.decorators import datasets_bundle_api_enabled
from cms.bundles.enums import BundleStatus
from cms.bundles.utils import (
    BundleAPIBundleMetadata,
    build_content_item_for_dataset,
    extract_content_id_from_bundle_response,
)

if TYPE_CHECKING:
    from cms.bundles.models import Bundle, BundleDataset

logger = logging.getLogger(__name__)


@dataclass
class BundleAPISyncService:
    """Keep a CMS bundle and the Bundle API in lockstep.

    CMS is the source of truth. On failure after creating a new remote bundle,
    the remote is deleted to avoid orphans. On any other failure we raise a
    ValidationError and let the transaction roll back.
    """

    bundle: "Bundle"
    api_client: BundleAPIClient
    original_datasets: set["BundleDataset"]

    @property
    def api_id(self) -> str:
        return self.bundle.bundle_api_bundle_id

    @cached_property
    def local_bundle_data(self) -> BundleAPIBundleMetadata:
        return BundleAPIBundleMetadata.from_bundle(self.bundle)

    @cached_property
    def api_bundle(self) -> dict:
        """Cached remote bundle response."""
        return self.api_client.get_bundle(self.api_id)

    @property
    def metadata_is_in_sync(self) -> bool:
        """Compare CMS bundle metadata with the API representation after normalisation.
        Returns True when identical.
        """
        return self.local_bundle_data.as_dict() == BundleAPIBundleMetadata.from_api_response(self.api_bundle).as_dict()

    @cached_property
    def bundled_datasets(self) -> set["BundleDataset"]:
        return set(self.bundle.bundled_datasets.all().select_related("dataset").order_by("id"))

    @datasets_bundle_api_enabled
    def sync(self) -> None:
        """Ensure the bundle in Wagtail is kept in sync with its corresponding bundle in the Bundle API.

        Flow
          1. Create the remote bundle if missing and there are datasets.
          2. Refresh local ETag if stale.
          3. If bundle is APPROVED or PUBLISHED, only sync state then stop.
          4. Reconcile contents first.
          5. Sync metadata after contents succeed.
        """
        # 1. Create the remote bundle if it does not exist and there are datasets
        create_remote_bundle = not self.api_id and self.bundled_datasets
        if create_remote_bundle:
            self._create_api_bundle()

        # If there is no remote bundle at this point, nothing more to do.
        if not self.api_id:
            return

        # 2. Make sure we hold the latest ETag
        etag_stale = self._refresh_local_etag_if_stale()

        try:
            # 3. State-only path for immutable bundles
            if self.bundle.status in {BundleStatus.APPROVED, BundleStatus.PUBLISHED}:
                # Approved and Published bundles are locked - CMS disallows edits to their
                # contents or metadata (beyond the status field itself). The Bundle API also
                # rejects such updates, so only the bundle’s status is synced here.

                # Any unexpected API-side changes to content items or bundle-level metadata
                # in these states indicate a data integrity issue and require manual investigation.

                # Other status transitions (e.g. DRAFT -> IN_REVIEW) are handled by
                # self._sync_metadata() to avoid redundant API calls.
                self._sync_bundle_state()
                return

            # 4. Sync content items before any metadata changes
            self._sync_contents(force_sync=etag_stale)

            # 5. Sync bundle metadata
            self._sync_metadata()
        except Exception as e:
            msg = "Failed to sync bundle with Bundle API"
            logger.exception(msg, extra={"id": self.bundle.pk, "api_id": self.api_id})

            # If we just created the remote bundle and any subsequent step failed,
            # best-effort delete to avoid orphans, then surface the original error.
            if create_remote_bundle:
                self._delete_api_bundle(raise_exceptions=False)

            if isinstance(e, ValidationError):
                raise
            raise ValidationError(msg) from e

    def _refresh_local_etag_if_stale(self) -> bool:
        """Update the local ETag from the API if it differs.
        Returns True if we refreshed it which implies stale before refresh.
        """
        current_api_etag: str = self.api_bundle.get("etag_header", "")
        stale = current_api_etag != self.bundle.bundle_api_etag
        if stale:
            logger.info(
                "Refreshing local bundle ETag from Bundle API",
                extra={
                    "id": self.bundle.pk,
                    "api_id": self.api_id,
                    "old_etag": self.bundle.bundle_api_etag,
                    "new_etag": current_api_etag,
                },
            )
            self.bundle.bundle_api_etag = current_api_etag
            self.bundle.save(update_fields=["bundle_api_etag"])
        return stale

    def _sync_bundle_state(self) -> None:
        """Align the remote bundle state with the CMS bundle.status if it differs."""
        state_changed = self.bundle.status != self.api_bundle.get("state", "")
        if not state_changed:
            return

        try:
            response = self.api_client.update_bundle_state(
                self.api_id, state=self.bundle.status, etag=self.bundle.bundle_api_etag
            )
            self.bundle.bundle_api_etag = response["etag_header"]
            self.bundle.save(update_fields=["bundle_api_etag"])
            logger.info(
                "Updated bundle state in Bundle API",
                extra={"id": self.bundle.pk, "api_id": self.api_id, "status": self.bundle.status},
            )
        except BundleAPIClientError as e:
            msg = "Failed to sync bundle state with Bundle API"
            logger.exception(msg, extra={"id": self.bundle.pk, "api_id": self.api_id, "status": self.bundle.status})
            raise ValidationError(msg) from e

    def _sync_contents(self, *, force_sync: bool = False) -> None:
        """Make the remote bundle contents exactly match CMS.

        If force_sync is True (etag stale), we always reconcile. Otherwise, we reconcile only when
        there is local content drift to push. Deletes the remote bundle if CMS has no datasets.
        """
        # If CMS has no datasets, delete the remote bundle entirely
        if not self.bundled_datasets:
            self._delete_api_bundle(raise_exceptions=True)
            return

        # Decide whether to reconcile in the non-forced path
        if not force_sync and not self._has_local_content_drift():
            return

        # Build desired CMS view
        cms_items: dict[str, BundleDataset] = {d.dataset.compound_id: d for d in self.bundled_datasets}

        # Fetch and index remote state
        api_contents = self.api_client.get_bundle_contents(self.api_id)
        api_index = self._index_api_contents(api_contents)

        cms_keys = set(cms_items.keys())
        api_keys = set(api_index.keys())

        to_add_keys = cms_keys - api_keys  # present in CMS only
        to_del_keys = api_keys - cms_keys  # present in API only
        to_link_keys = {  # present in both, but local link missing
            k for k in (cms_keys & api_keys) if not cms_items[k].bundle_api_content_id
        }

        add_items: set[BundleDataset] = {cms_items[k] for k in to_add_keys}
        delete_items: dict[str, str] = {k: api_index[k] for k in to_del_keys}

        # Backfill local content ids for items already existing remotely
        self._backfill_missing_content_ids(
            to_link_keys=to_link_keys,
            cms_items=cms_items,
            api_index=api_index,
        )

        # Apply API changes, capturing latest ETag
        etag_after_add = self._add_content_items(items=add_items)
        etag_after_delete = self._delete_content_items(items=delete_items)

        # Persist the newest ETag after a successful reconciliation
        final_etag = etag_after_delete or etag_after_add
        if final_etag and final_etag != self.bundle.bundle_api_etag:
            self.bundle.bundle_api_etag = final_etag
            self.bundle.save(update_fields=["bundle_api_etag"])

    def _has_local_content_drift(self) -> bool:
        """Determine if the current CMS set implies API reconciliation.

        True when any of the following hold:
          - a removed dataset, regardless of content id presence
          - a current dataset is missing a content id which implies add or link
        """
        removed = self.original_datasets - self.bundled_datasets
        # If any items were removed, we *always* need to reconcile.
        if removed:
            return True

        # If no items were removed, check if we need to add/link ones in bundled_datasets
        has_items_to_add_or_link = any(not d.bundle_api_content_id for d in self.bundled_datasets)
        return has_items_to_add_or_link

    def _backfill_missing_content_ids(
        self,
        *,
        to_link_keys: Iterable[str],
        cms_items: dict[str, "BundleDataset"],
        api_index: dict[str, str],
    ) -> None:
        """Populate local bundle_api_content_id for items that already exist
        in the API but are missing it locally.
        """
        datasets_to_update = []
        for key in to_link_keys:
            bundled_dataset = cms_items[key]
            content_id = api_index[key]
            if bundled_dataset.bundle_api_content_id != content_id:
                bundled_dataset.bundle_api_content_id = content_id
                datasets_to_update.append(bundled_dataset)

        if datasets_to_update:
            logger.info(
                "Backfilled missing bundle_api_content_id for existing content items",
                extra={
                    "id": self.bundle.pk,
                    "api_id": self.api_id,
                    "count": len(datasets_to_update),
                },
            )
            self.bundle.bundled_datasets.bulk_update(datasets_to_update, ["bundle_api_content_id"])

    def _add_content_items(
        self,
        *,
        items: set["BundleDataset"],
    ) -> str | None:
        """Add content items to the remote bundle.
        Stops on first error. Returns the most recent ETag observed.
        """
        if not items:
            return None

        etag = None
        for item in items:
            content_item = build_content_item_for_dataset(item.dataset)
            try:
                # Client handles If-Match internally. We only read the returned ETag.
                response = self.api_client.add_content_to_bundle(
                    bundle_id=self.api_id,
                    content_item=content_item,
                )
                etag = response["etag_header"]

                content_id = extract_content_id_from_bundle_response(response, item.dataset)
                if not content_id:
                    msg = (
                        f"Failed to add dataset to bundle in Bundle API. "
                        f"Bundle API did not return a content ID for the added dataset - {item.dataset}"
                    )
                    logger.error(
                        msg, extra={"id": self.bundle.pk, "api_id": self.api_id, "dataset": item.dataset.compound_id}
                    )
                    raise ValidationError(msg)

                item.bundle_api_content_id = content_id
                item.save(update_fields=["bundle_api_content_id"])

                logger.info(
                    "Added content to bundle in Bundle API",
                    extra={
                        "id": self.bundle.pk,
                        "api_id": self.api_id,
                        "content_id": content_id,
                        "dataset": item.dataset.compound_id,
                    },
                )
            except BundleAPIClientError as e:
                msg = f"Failed to add dataset to bundle in Bundle API - {item.dataset}"
                logger.exception(
                    msg, extra={"id": self.bundle.pk, "api_id": self.api_id, "dataset": item.dataset.compound_id}
                )
                raise ValidationError(msg) from e

        return etag

    def _delete_content_items(
        self,
        *,
        items: dict[str, str],
    ) -> str | None:
        """Remove content items from the remote bundle.
        Stops on first error. Returns the most recent ETag observed.
        """
        if not items:
            return None

        etag = None
        for compound_id, content_id in items.items():
            try:
                response = self.api_client.delete_content_from_bundle(
                    bundle_id=self.api_id,
                    content_id=content_id,
                )
                etag = response["etag_header"]

                logger.info(
                    "Deleted content from bundle in Bundle API",
                    extra={"id": self.bundle.pk, "api_id": self.api_id, "dataset": compound_id},
                )
            except BundleAPIClientError as e:
                dataset_id, edition_id, version_id = compound_id.split(",")
                suffix = f"Dataset ID: {dataset_id}, Edition ID: {edition_id}, Version ID: {version_id}"
                msg = f"Failed to delete dataset from bundle in Bundle API - {suffix}"
                logger.exception(msg, extra={"id": self.bundle.pk, "api_id": self.api_id, "dataset": compound_id})
                raise ValidationError(msg) from e

        return etag

    def _sync_metadata(self) -> None:
        """Update bundle-level metadata in the API when it differs from CMS."""
        if not self.api_id:
            return

        if self.metadata_is_in_sync:
            return

        response = self.api_client.update_bundle(
            bundle_id=self.api_id,
            bundle_data=self.local_bundle_data,
            etag=self.bundle.bundle_api_etag,
        )

        self.bundle.bundle_api_etag = response["etag_header"]
        self.bundle.save(update_fields=["bundle_api_etag"])
        logger.info("Synced bundle metadata with Bundle API", extra={"id": self.bundle.pk, "api_id": self.api_id})

    def _get_bundle_data_for_create(self) -> BundleAPIBundleMetadata:
        """Return a payload for remote bundle create. New remote bundles start as DRAFT.
        The eventual status is reconciled by _sync_metadata().
        """
        return (
            self.local_bundle_data
            if self.bundle.status == BundleStatus.DRAFT
            else replace(self.local_bundle_data, state=BundleStatus.DRAFT)
        )

    def _create_api_bundle(self) -> None:
        """Create the remote bundle and persist returned id and ETag locally.
        On failure to persist locally, best-effort delete the remote and raise.
        """
        bundle_data = self._get_bundle_data_for_create()

        try:
            response = self.api_client.create_bundle(bundle_data)
            bundle_api_bundle_id = str(response["id"])
            bundle_api_etag = response.get("etag_header", "")
            logger.info("Created bundle in Bundle API", extra={"id": self.bundle.pk, "api_id": bundle_api_bundle_id})
        except (BundleAPIClientError, KeyError) as e:
            msg = "Failed to create bundle in Bundle API"
            logger.exception(msg, extra={"id": self.bundle.pk})
            raise ValidationError(msg) from e

        try:
            self.bundle.bundle_api_bundle_id = bundle_api_bundle_id
            self.bundle.bundle_api_etag = bundle_api_etag
            self.bundle.save(update_fields=["bundle_api_bundle_id", "bundle_api_etag"])
        except Exception as e:
            logger.exception(
                "Failed to save bundle API metadata after creating bundle in Bundle API, deleting remote bundle",
                extra={"id": self.bundle.pk, "api_id": self.api_id},
            )
            self._delete_api_bundle(bundle_api_bundle_id=bundle_api_bundle_id, raise_exceptions=True)
            raise ValidationError("Failed to save bundle API metadata after creating bundle in Bundle API") from e

    def _delete_api_bundle(self, *, bundle_api_bundle_id: str | None = None, raise_exceptions: bool) -> None:
        """Delete the remote bundle and clear local id and ETag.

        If raise_exceptions is True, re-raise non-404 failures as ValidationError.
        This method is best-effort to avoid orphans.
        """
        api_id = bundle_api_bundle_id or self.api_id
        if not api_id:
            return

        deletion_failed = False
        try:
            self.api_client.delete_bundle(api_id)
            logger.info("Deleted bundle from Bundle API", extra={"id": self.bundle.pk, "api_id": api_id})
        except BundleAPIClientError404:
            logger.warning(
                "Bundle not found in Bundle API when attempting to delete",
                extra={"id": self.bundle.pk, "api_id": api_id},
            )
        except Exception as e:  # pylint: disable=broad-exception-caught
            deletion_failed = True
            msg = "Failed to delete bundle from Bundle API"
            logger.exception(msg, extra={"id": self.bundle.pk, "api_id": api_id})
            if raise_exceptions:
                if isinstance(e, ValidationError):
                    raise
                raise ValidationError(msg) from e
        finally:
            if not deletion_failed:
                self.bundle.bundle_api_bundle_id = ""
                self.bundle.bundle_api_etag = ""
                self.bundle.save(update_fields=["bundle_api_bundle_id", "bundle_api_etag"])

    @staticmethod
    def _index_api_contents(api_contents: dict) -> dict[str, str]:
        """Build a lookup of compound key to content id.

        Key format: "{dataset_id},{edition_id},{version_id}".
        """
        index: dict[str, str] = {}
        for item in api_contents.get("items", []):
            md = item.get("metadata", {}) or {}
            dataset_id = md.get("dataset_id")
            edition_id = md.get("edition_id")
            version_id = md.get("version_id")
            item_id = item.get("id")

            if all([dataset_id, edition_id, version_id, item_id]):
                key = f"{dataset_id},{edition_id},{version_id}"
                index[key] = item_id

        return index
