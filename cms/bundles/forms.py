import logging
from datetime import datetime
from functools import cached_property
from typing import TYPE_CHECKING, Any

from django import forms
from django.core.exceptions import ValidationError
from django.template.defaultfilters import pluralize
from django.utils import timezone

from cms.bundles.clients.api import (
    BundleAPIClient,
    BundleAPIClientError,
)
from cms.bundles.decorators import datasets_bundle_api_enabled
from cms.bundles.enums import ACTIVE_BUNDLE_STATUS_CHOICES, EDITABLE_BUNDLE_STATUSES, BundleStatus
from cms.core.forms import DeduplicateInlinePanelAdminForm
from cms.workflows.models import ReadyToPublishGroupTask

from .bundle_api_sync_service import BundleAPISyncService

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from .models import Bundle


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

    @cached_property
    def bundle_api_client(self) -> BundleAPIClient:
        return BundleAPIClient(access_token=self.datasets_bundle_api_user_access_token)

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

        try:
            response = self.bundle_api_client.get_bundle_contents(self.instance.bundle_api_bundle_id)

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
        """Validate that all bundled datasets are approved in
        the Bundle API when bundle is set to approved status.

        This validation checks the dataset status in the API.
        If there have been previous sync issues, the Wagtail state and API state may
        differ. Since approval is a finalising step, the authoritative state must
        match what is stored in the API.

        If a bundle needs reconciliation, its status can still be moved back from
        "approved" to allow normal reconciliation on save. This scenario is expected
        only in edge cases.
        """
        # Skip validation if bundle doesn't have an API ID yet, or it doesn't have any datasets
        if not self.instance.bundle_api_bundle_id and not self._has_datasets():
            return

        datasets_not_approved = self._get_unapproved_bundle_contents()

        if datasets_not_approved:
            num_not_approved = len(datasets_not_approved)
            errors = [
                f"Cannot approve the bundle with {num_not_approved} dataset{pluralize(num_not_approved)} "
                f"not ready to be published:",
                *datasets_not_approved,
            ]

            raise ValidationError(errors)

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

    def _sync_with_bundle_api(self, bundle: "Bundle") -> None:
        sync_service = BundleAPISyncService(
            bundle=bundle,
            api_client=self.bundle_api_client,
            original_datasets=self.original_datasets,
        )
        sync_service.sync()

    def save(self, commit: bool = True) -> "Bundle":
        """Save the bundle and create in API if it has datasets but no API ID."""
        # Use the standard save behavior first. This handles new/existing objects
        # and m2m relations if commit=True.
        bundle: Bundle = super().save(commit=commit)

        if commit:
            self._sync_with_bundle_api(bundle)
        return bundle
