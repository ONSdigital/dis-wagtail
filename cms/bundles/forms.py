import logging
from datetime import datetime
from typing import TYPE_CHECKING, Any

from django import forms
from django.core.exceptions import ValidationError
from django.template.defaultfilters import pluralize
from django.utils import timezone

from cms.bundles.clients.api import (
    BundleAPIClient,
    BundleAPIClientError,
    build_content_item_for_dataset,
    extract_content_id_from_bundle_response,
)
from cms.bundles.decorators import datasets_bundle_api_enabled
from cms.bundles.enums import ACTIVE_BUNDLE_STATUS_CHOICES, EDITABLE_BUNDLE_STATUSES, BundleStatus
from cms.bundles.utils import build_bundle_data_for_api
from cms.core.forms import DeduplicateInlinePanelAdminForm
from cms.workflows.models import ReadyToPublishGroupTask

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from .models import Bundle, BundleDataset


class BundleAdminForm(DeduplicateInlinePanelAdminForm):
    """The Bundle admin form used in the add/edit interface."""

    instance: "Bundle"

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Helps the form initialisation.

        - Hides the "Released" status choice as that happens on publish
        - disabled/hide the approved at/by fields
        """
        self.datasets_bundle_api_user_access_token = kwargs.pop("access_token", None)

        super().__init__(*args, **kwargs)
        # hide the status field, and exclude the "Released" status choice
        self.fields["status"].widget = forms.HiddenInput()
        if self.instance.status in EDITABLE_BUNDLE_STATUSES:
            self.fields["status"].choices = ACTIVE_BUNDLE_STATUS_CHOICES
        elif self.instance.status == BundleStatus.APPROVED.value:
            fields_to_exclude_from_being_disabled = ["status"]
            if "data" in kwargs and kwargs["data"].get("status") == BundleStatus.DRAFT.value:
                if self.instance.release_calendar_page_id:
                    fields_to_exclude_from_being_disabled.append("release_calendar_page")
                elif self.instance.publication_date:
                    fields_to_exclude_from_being_disabled.append("publication_date")

            # disable all direct fields
            for field_name in self.fields:
                if field_name not in fields_to_exclude_from_being_disabled:
                    self.fields[field_name].disabled = True

            if "data" in kwargs and kwargs["data"].get("status") != BundleStatus.APPROVED.value:
                # the form is initialised in a POST request, and the status has changed
                # drop the InlinePanel formsets (bundle_pages, bundle_datasets, teams) so
                # no changes are made
                self.formsets: dict[str, Any] = {}
            else:
                # we're initializing the form with GET, tell th InlinePanel formsets they cannot
                # add more items, so the "Add X" button is not shown
                for formset in self.formsets.values():
                    formset.max_num = len(formset.forms)

        # fully hide and disable the approved_at/by fields to prevent form tampering
        self.fields["approved_at"].disabled = True
        self.fields["approved_at"].widget = forms.HiddenInput()
        self.fields["approved_by"].disabled = True
        self.fields["approved_by"].widget = forms.HiddenInput()

        self.original_status = self.instance.status

        self.original_datasets = set(self.instance.bundled_datasets.all().order_by("id").select_related("dataset"))
        self.original_teams = set(self.instance.teams.all().order_by("id").select_related("team"))

    def _formsets_have_changes(self) -> bool:
        """Detect any adds/edits/deletes in our inline panels."""
        for key in ("bundled_pages", "bundled_datasets", "teams"):
            formset = self.formsets.get(key)
            if not formset:
                continue
            # any delete/add/change counts as a change
            if formset.deleted_forms:
                return True
            for form in formset.forms:
                # Ignore empty forms and forms marked for deletion
                if form.cleaned_data.get("DELETE"):
                    return True  # deleting a specific row
                if form.has_changed():
                    return True
        return False

    def _has_datasets(self) -> bool:
        has_datasets = False
        if "bundled_datasets" not in self.formsets:
            return False
        for form in self.formsets["bundled_datasets"].forms:
            if not form.is_valid() or form.cleaned_data.get("DELETE"):
                continue

            if form.clean().get("dataset"):
                has_datasets = True
                break

        return has_datasets

    def _get_dataset_title_from_form_data(self, dataset_id: str) -> str:
        """Get dataset title from form data based on dataset ID."""
        for form in self.formsets["bundled_datasets"].forms:
            if (
                form.is_valid()
                and not form.cleaned_data.get("DELETE")
                and (dataset := form.cleaned_data.get("dataset"))
                and dataset.namespace == dataset_id
            ):
                return str(dataset.title)
        return dataset_id

    def _get_unapproved_bundle_contents(self) -> list[str]:
        """Check bundle contents and return list of non-approved datasets."""
        datasets_not_approved: list[str] = []

        # Ensure bundle_api_bundle_id is not None
        if not self.instance.bundle_api_bundle_id:
            return datasets_not_approved

        client = BundleAPIClient(access_token=self.datasets_bundle_api_user_access_token)
        try:
            response = client.get_bundle_contents(self.instance.bundle_api_bundle_id)

            # update the etag value
            self.instance.bundle_api_etag = response["etag_header"]
            self.instance.save(update_fields=["bundle_api_etag"])

            # Check each content item in the bundle
            for item in response.get("items", []):
                item_state = item.get("state", "unknown")

                if item_state != BundleStatus.APPROVED.value:
                    # Find the corresponding dataset title from the metadata
                    metadata = item.get("metadata", {})
                    dataset_id = metadata.get("dataset_id", "unknown")
                    dataset_edition = metadata.get("edition_id", "unknown")
                    dataset_title = self._get_dataset_title_from_form_data(dataset_id)
                    datasets_not_approved.append(f"{dataset_title} (Edition: {dataset_edition}, Status: {item_state})")

        except BundleAPIClientError as e:
            logger.exception("Failed to check bundle contents for bundle %s: %s", self.instance.bundle_api_bundle_id, e)
            datasets_not_approved.append("Bundle content validation failed")

        return datasets_not_approved

    @datasets_bundle_api_enabled
    def _validate_bundled_datasets_status(self) -> None:
        """Validate that all bundled datasets are approved when bundle is set to approved status."""
        # Skip validation if bundle doesn't have an API ID yet, or it doesn't have any datasets
        if not self.instance.bundle_api_bundle_id and not self._has_datasets():
            return

        datasets_not_approved = self._get_unapproved_bundle_contents()

        if datasets_not_approved:
            # Return the original status
            self.cleaned_data["status"] = self.instance.status
            dataset_list = ", ".join(datasets_not_approved)
            num_not_approved = len(datasets_not_approved)
            raise ValidationError(
                f"Cannot approve the bundle with {num_not_approved} dataset{pluralize(num_not_approved)} "
                f"not ready to be published: {dataset_list}"
            )

    def _validate_bundled_pages(self) -> None:
        """Validates related pages to ensure the selected page is not in another active bundle."""
        if "bundled_pages" not in self.formsets:
            return
        for form in self.formsets["bundled_pages"].forms:
            if not form.is_valid():
                continue

            page = form.clean().get("page")

            if not form.cleaned_data.get("DELETE"):
                page = page.specific
                if page.in_active_bundle and page.active_bundle != self.instance:
                    raise ValidationError(f"'{page}' is already in an active bundle ({page.active_bundle})")
                if self.cleaned_data.get("release_calendar_page") == page:
                    raise ValidationError(f"'{page}' is already set as the Release Calendar page for this bundle.")

    def _validate_bundled_pages_status(self) -> None:
        has_pages = False
        num_pages_not_ready = 0
        if "bundled_pages" not in self.formsets:
            return

        for form in self.formsets["bundled_pages"].forms:
            if not form.is_valid() or form.cleaned_data.get("DELETE"):
                continue

            if page := form.clean().get("page"):
                has_pages = True
                page = page.specific
                workflow_state = page.current_workflow_state

                if not (
                    workflow_state
                    and isinstance(workflow_state.current_task_state.task.specific, ReadyToPublishGroupTask)
                ):
                    form.add_error("page", "This page is not ready to be published")
                    num_pages_not_ready += 1

        if not has_pages and not self._has_datasets():
            raise ValidationError("Cannot approve the bundle without any pages or datasets")

        if num_pages_not_ready:
            self.cleaned_data["status"] = self.instance.status
            raise ValidationError(
                f"Cannot approve the bundle with {num_pages_not_ready} "
                f"page{pluralize(num_pages_not_ready)} not ready to be published."
            )

    def _validate_publication_date(self) -> None:
        release_calendar_page = self.cleaned_data["release_calendar_page"]
        publication_date = self.cleaned_data["publication_date"]

        if release_calendar_page and publication_date:
            error = "You must choose either a Release Calendar page or a Publication date, not both."
            self.add_error("release_calendar_page", error)
            self.add_error("publication_date", error)

        if (
            release_calendar_page
            and release_calendar_page.release_date < timezone.now()
            and not self.instance.can_be_manually_published
        ):
            error = "The release date on the release calendar page cannot be in the past."
            raise ValidationError({"release_calendar_page": error})

        if publication_date and publication_date < timezone.now() and not self.instance.can_be_manually_published:
            raise ValidationError({"publication_date": "The release date cannot be in the past."})

    def _validate_no_changes_on_approve(self) -> None:
        """Validates that no other changes are made when approving a bundle.

        To avoid mixing two different kinds of changes in one action, bundle
        approvals are not permitted at the same time as other edits. The user must
        first save any changes, then approve the bundle in a separate step.
        """
        allowed = {"status", "approved_at", "approved_by"}
        disallowed_changes = [field for field in self.changed_data if field not in allowed]
        if disallowed_changes:
            raise ValidationError(
                dict.fromkeys(
                    disallowed_changes,
                    "You cannot make changes to this field when approving a bundle. "
                    "Please save your changes first, then Approve the bundle in a separate step.",
                )
            )

        if self._formsets_have_changes():
            raise ValidationError(
                "You cannot make changes to pages, datasets, or teams when approving a bundle. "
                "Please save your changes first, then Approve the bundle in a separate step."
            )

    def _validate_approval(self) -> None:
        if self.cleaned_data.get("status") != BundleStatus.APPROVED.value:
            return

        try:
            # ensure no other changes are made when approving
            self._validate_no_changes_on_approve()

            # ensure all bundled pages are ready to publish
            self._validate_bundled_pages_status()

            # ensure all bundled datasets are approved (the function will check if the API is enabled)
            self._validate_bundled_datasets_status()
        except ValidationError as e:
            # revert the status change back to original to prevent "Approve" specific logic from applying
            self.cleaned_data["status"] = self.instance.status
            raise e

    def clean_publication_date(self) -> datetime | None:
        # Set seconds to 0 to make scheduling less surprising
        if publication_date := self.cleaned_data["publication_date"]:
            return publication_date.replace(second=0)  # type: ignore[no-any-return]
        return None

    def clean(self) -> dict[str, Any] | None:
        """Validates the form.

        - the bundle cannot be approved if any the referenced pages are not ready to be published
        - tidies up/ populates approved at/by
        """
        cleaned_data: dict[str, Any] = super().clean()

        # On approval, this must run before any other validation
        self._validate_approval()

        self._validate_publication_date()

        # deduplicate entries
        self.deduplicate_formset(formset="bundled_pages", target_field="page")
        self.deduplicate_formset(formset="bundled_datasets", target_field="dataset")
        self.deduplicate_formset(formset="teams", target_field="team")

        self._validate_bundled_pages()

        submitted_status = cleaned_data["status"]
        if self.instance.status != submitted_status:
            # the status has changed
            if submitted_status == BundleStatus.APPROVED:
                cleaned_data["approved_at"] = timezone.now()
                cleaned_data["approved_by"] = self.for_user
            elif self.instance.status == BundleStatus.APPROVED:
                # the bundle was approved, and is now unapproved.
                cleaned_data["approved_at"] = None
                cleaned_data["approved_by"] = None

                # we went from "ready to publish" to a lower status, preserve the linked RC or publication date
                if self.instance.release_calendar_page:
                    cleaned_data["release_calendar_page"] = self.instance.release_calendar_page
                elif self.instance.publication_date:
                    cleaned_data["publication_date"] = self.instance.publication_date

        return cleaned_data

    @datasets_bundle_api_enabled
    def _push_bundle_to_bundle_api(self, client: BundleAPIClient, bundle: "Bundle") -> "Bundle":
        """Pushes the bundle to the Bundle API if it does."""
        try:
            # Create the bundle in the API with the correct payload
            bundle_data = build_bundle_data_for_api(bundle)
            response = client.create_bundle(bundle_data)

            bundle.bundle_api_bundle_id = str(response["id"])
            bundle.bundle_api_etag = response["etag_header"]
            bundle.save(update_fields=["bundle_api_bundle_id", "bundle_api_etag"])
            logger.info("Created bundle %s in Bundle API with ID: %s", bundle.pk, bundle.bundle_api_bundle_id)
            return bundle

        except (BundleAPIClientError, KeyError) as e:
            logger.exception("Failed to create bundle %s in Bundle API: %s", bundle.pk, e)
            raise ValidationError("Could not communicate with the Bundle API") from e

    @datasets_bundle_api_enabled
    def _sync_bundle_status_with_bundle_api(self, client: BundleAPIClient, bundle: "Bundle") -> None:
        if not bundle.bundle_api_bundle_id:
            return

        try:
            response = client.update_bundle_state(bundle.bundle_api_bundle_id, bundle.status, bundle.bundle_api_etag)

            bundle.bundle_api_etag = response["etag_header"]
            bundle.save(update_fields=["bundle_api_etag"])
            logger.info("Updated bundle %s status to %s in Bundle API", bundle.pk, bundle.status)
        except BundleAPIClientError as e:
            logger.exception("Failed to sync bundle %s with Bundle API: %s", bundle.pk, e)
            raise ValidationError("Could not communicate with the Bundle API") from e

    @datasets_bundle_api_enabled
    def _sync_datasets_with_bundle_api(
        self, client: BundleAPIClient, bundle: "Bundle", current_datasets: set["BundleDataset"]
    ) -> None:
        """Sync dataset changes to the API."""
        if not bundle.bundle_api_bundle_id:
            return

        if not current_datasets:
            # If we have no more dataset, remove the bundle from the API
            try:
                client.delete_bundle(bundle.bundle_api_bundle_id)
                logger.info("Deleted bundle %s from Bundle API", bundle.pk)
                bundle.bundle_api_bundle_id = ""
                bundle.bundle_api_etag = ""
                bundle.save(update_fields=["bundle_api_bundle_id", "bundle_api_etag"])
            except BundleAPIClientError as e:
                logger.exception("Failed to delete bundle %s from Bundle API: %s", bundle.pk, e)
                raise ValidationError("Could not communicate with the Bundle API") from e
            return

        # Calculate diffs
        added = {d for d in current_datasets - self.original_datasets if not d.bundle_api_content_id}
        removed = {d for d in self.original_datasets - current_datasets if d.bundle_api_content_id}
        common_but_not_linked = {d for d in self.original_datasets & current_datasets if not d.bundle_api_content_id}

        # Add or link items
        etag_after_addition = self._handle_api_add_items(
            client=client,
            bundle=bundle,
            items=(added | common_but_not_linked),
        )

        # Remove items
        etag_after_deletion = self._handle_api_delete_items(
            client=client,
            bundle=bundle,
            items=removed,
        )

        # Persist the final ETag once everything has succeeded
        final_etag = etag_after_deletion or etag_after_addition
        if final_etag and final_etag != bundle.bundle_api_etag:
            bundle.bundle_api_etag = final_etag
            bundle.save(update_fields=["bundle_api_etag"])

    @staticmethod
    def _handle_api_add_items(
        *,
        client: BundleAPIClient,
        bundle: "Bundle",
        items: set["BundleDataset"],
    ) -> str | None:
        """Add or link content items to the bundle. Stops on first error. Advances ETag after each success."""
        if not items:
            return None

        etag = None
        for item in items:
            content_item = build_content_item_for_dataset(item.dataset)
            try:
                # Client handles If-Match internally. We only read the returned ETag.
                response = client.add_content_to_bundle(
                    bundle_id=bundle.bundle_api_bundle_id,
                    content_item=content_item,
                )
                etag = response["etag_header"]

                content_id = extract_content_id_from_bundle_response(response, item.dataset)
                if not content_id:
                    logger.error(
                        "Could not find content_id in response for bundle",
                        extra={"id": bundle.pk, "api_id": bundle.bundle_api_bundle_id},
                    )
                    raise ValidationError("Bundle API did not return an ID for the added content")

                item.bundle_api_content_id = content_id
                item.save(update_fields=["bundle_api_content_id"])

                logger.info(
                    "Added content %s to bundle %s in Bundle API with ID %s",
                    item.dataset.namespace,
                    bundle.pk,
                    content_id,
                )
            except BundleAPIClientError as e:
                logger.exception("Failed to add content to bundle %s in Bundle API: %s", bundle.pk, e)
                raise ValidationError("Could not communicate with the Bundle API") from e

        return etag

    @staticmethod
    def _handle_api_delete_items(
        *,
        client: BundleAPIClient,
        bundle: "Bundle",
        items: set["BundleDataset"],
    ) -> str | None:
        """Remove content items from the bundle. Stops on first error. Advances ETag after each success."""
        if not items:
            return None

        etag = None
        for item in items:
            content_id = item.bundle_api_content_id
            try:
                # Client handles If-Match internally. We only read the returned ETag.
                response = client.delete_content_from_bundle(
                    bundle_id=bundle.bundle_api_bundle_id,
                    content_id=content_id,
                )
                etag = response["etag_header"]

                logger.info("Deleted content %s from bundle %s in Bundle API", content_id, bundle.pk)
            except BundleAPIClientError as e:
                logger.exception(
                    "Failed to delete content %s from bundle %s in Bundle API: %s", content_id, bundle.pk, e
                )
                raise ValidationError("Could not communicate with the Bundle API") from e

        return etag

    @datasets_bundle_api_enabled
    def _sync_teams_with_bundle_api(self, client: BundleAPIClient, bundle: "Bundle") -> None:
        if not bundle.bundle_api_bundle_id:
            return

        bundle_data = build_bundle_data_for_api(bundle)

        try:
            response = client.update_bundle(
                bundle_id=bundle.bundle_api_bundle_id, bundle_data=bundle_data, etag=bundle.bundle_api_etag
            )
            bundle.bundle_api_etag = response["etag_header"]
            bundle.save(update_fields=["bundle_api_etag"])
            logger.info(
                "Successfully synced preview teams for bundle %s (Wagtail ID: %s).",
                bundle.bundle_api_bundle_id,
                bundle.pk,
            )
        except BundleAPIClientError as e:
            logger.exception(
                "Failed to sync preview teams for bundle %s (Wagtail ID: %s): %s",
                bundle.bundle_api_bundle_id,
                bundle.pk,
                e,
            )
            raise ValidationError("Could not communicate with the Bundle API") from e

    @datasets_bundle_api_enabled
    def _check_and_sync_with_bundle_api(self, bundle: "Bundle") -> None:
        should_push_bundle_to_api = not bundle.bundle_api_bundle_id and self._has_datasets()
        status_has_changed = bundle.bundle_api_bundle_id and self.original_status != bundle.status

        current_datasets = set(bundle.bundled_datasets.all().select_related("dataset").order_by("id"))
        should_push_dataset_changes_to_api = self.original_datasets != current_datasets
        should_push_team_changes_to_api = self.original_teams != set(
            bundle.teams.all().select_related("team").order_by("id")
        )
        if (
            should_push_bundle_to_api
            or status_has_changed
            or should_push_dataset_changes_to_api
            or should_push_team_changes_to_api
        ):
            client = BundleAPIClient(access_token=self.datasets_bundle_api_user_access_token)
            if should_push_bundle_to_api:
                # The bundle should be created in the API if it has datasets, and it doesn't have an API ID.
                bundle = self._push_bundle_to_bundle_api(client, bundle)
            if status_has_changed:
                self._sync_bundle_status_with_bundle_api(client, bundle)
            if should_push_dataset_changes_to_api:
                self._sync_datasets_with_bundle_api(client, bundle, current_datasets)
            if should_push_team_changes_to_api:
                self._sync_teams_with_bundle_api(client, bundle)

    def save(self, commit: bool = True) -> "Bundle":
        """Save the bundle and create in API if it has datasets but no API ID."""
        # Use the standard save behavior first. This handles new/existing objects
        # and m2m relations if commit=True.
        bundle: Bundle = super().save(commit=commit)

        if commit:
            self._check_and_sync_with_bundle_api(bundle)
        return bundle
