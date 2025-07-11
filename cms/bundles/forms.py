import logging
from typing import TYPE_CHECKING, Any

from django import forms
from django.conf import settings
from django.core.exceptions import ValidationError
from django.template.defaultfilters import pluralize
from django.utils import timezone
from wagtail.admin.forms import WagtailAdminModelForm

from cms.bundles.api import BundleAPIClient, BundleAPIClientError
from cms.bundles.decorators import ons_bundle_api_enabled
from cms.bundles.enums import ACTIVE_BUNDLE_STATUS_CHOICES, EDITABLE_BUNDLE_STATUSES, BundleStatus
from cms.bundles.utils import _build_bundle_data_for_api
from cms.workflows.models import ReadyToPublishGroupTask

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from .models import Bundle


class BundleAdminForm(WagtailAdminModelForm):
    """The Bundle admin form used in the add/edit interface."""

    instance: "Bundle"

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Helps the form initialisation.

        - Hides the "Released" status choice as that happens on publish
        - disabled/hide the approved at/by fields
        """
        super().__init__(*args, **kwargs)
        # hide the "Released" status choice
        if self.instance.status in EDITABLE_BUNDLE_STATUSES:
            self.fields["status"].choices = ACTIVE_BUNDLE_STATUS_CHOICES
        elif self.instance.status == BundleStatus.APPROVED.value:
            fields_to_exclude_from_being_disabled = ["status"]
            if "data" in kwargs and kwargs["data"].get("status") == BundleStatus.DRAFT.value:
                if self.instance.release_calendar_page_id:
                    fields_to_exclude_from_being_disabled.append("release_calendar_page")
                elif self.instance.publication_date:
                    fields_to_exclude_from_being_disabled.append("publication_date")

            for field_name in self.fields:
                if field_name not in fields_to_exclude_from_being_disabled:
                    self.fields[field_name].disabled = True

        # fully hide and disable the approved_at/by fields to prevent form tampering
        self.fields["approved_at"].disabled = True
        self.fields["approved_at"].widget = forms.HiddenInput()
        self.fields["approved_by"].disabled = True
        self.fields["approved_by"].widget = forms.HiddenInput()

        self.original_status = self.instance.status

    def _has_datasets(self) -> bool:
        has_datasets = False
        for form in self.formsets["bundled_datasets"].forms:
            if not form.is_valid() or form.cleaned_data["DELETE"]:
                continue

            if form.clean().get("dataset"):
                has_datasets = True
                break

        return has_datasets

    @ons_bundle_api_enabled
    def _validate_bundled_datasets_status(self) -> None:
        """Validate that all bundled datasets are approved when bundle is set to approved status."""
        if not self._has_datasets():
            return

        client = BundleAPIClient()
        datasets_not_approved = []

        for form in self.formsets["bundled_datasets"].forms:
            if not form.is_valid():
                continue

            if form.cleaned_data.get("DELETE"):
                continue

            if dataset := form.cleaned_data.get("dataset"):
                try:
                    response = client.get_dataset_status(dataset.namespace)
                    dataset_status = response.get("status", "unknown")

                    if dataset_status != "approved":
                        datasets_not_approved.append(f"{dataset.title} (status: {dataset_status})")

                except BundleAPIClientError as e:
                    logger.error("Failed to check status for dataset %s: %s", dataset.namespace, e)
                    datasets_not_approved.append(f"{dataset.title} (status check failed)")

        if datasets_not_approved:
            # Return the original status
            self.cleaned_data["status"] = self.instance.status
            dataset_list = ", ".join(datasets_not_approved)
            raise ValidationError(
                f"Cannot approve the bundle with dataset{pluralize(len(datasets_not_approved))} "
                f"not ready to be published: {dataset_list}"
            )

    def _validate_bundled_pages(self) -> None:
        """Validates and tidies up related pages.

        - if we have an empty page reference, remove it form the form data
        - ensure the selected page is not in another active bundle.
        """
        chosen = []
        for idx, form in enumerate(self.formsets["bundled_pages"].forms):
            if not form.is_valid():
                continue

            page = form.clean().get("page")
            if page is None:
                # tidy up in case the page reference is empty
                self.formsets["bundled_pages"].forms[idx].cleaned_data["DELETE"] = True
                continue

            if page in chosen:
                # we saw this already, mark for removal to avoid duplicates.
                self.formsets["bundled_pages"].forms[idx].cleaned_data["DELETE"] = True
                continue

            chosen.append(page)

            if not form.cleaned_data["DELETE"]:
                page = page.specific
                if page.in_active_bundle and page.active_bundle != self.instance:
                    raise ValidationError(f"'{page}' is already in an active bundle ({page.active_bundle})")
                if self.cleaned_data.get("release_calendar_page") == page:
                    raise ValidationError(f"'{page}' is already set as the Release Calendar page for this bundle.")

    def _validate_bundled_pages_status(self) -> None:
        has_pages = False
        num_pages_not_ready = 0
        for form in self.formsets["bundled_pages"].forms:
            if form.cleaned_data["DELETE"]:
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

        if release_calendar_page and release_calendar_page.release_date < timezone.now():
            error = "The release date on the release calendar page cannot be in the past."
            raise ValidationError({"release_calendar_page": error})

        if publication_date and publication_date < timezone.now():
            raise ValidationError({"publication_date": "The release date cannot be in the past."})

    def clean(self) -> dict[str, Any] | None:
        """Validates the form.

        - the bundle cannot be approved if any the referenced pages are not ready to be published
        - tidies up/ populates approved at/by
        """
        cleaned_data: dict[str, Any] = super().clean()

        self._validate_publication_date()

        self._validate_bundled_pages()

        submitted_status = cleaned_data["status"]
        if self.instance.status != submitted_status:
            # the status has changed
            if submitted_status == BundleStatus.APPROVED:
                # ensure all bundled pages are ready to publish
                self._validate_bundled_pages_status()

                # ensure all bundled datasets are approved
                self._validate_bundled_datasets_status()

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

    def save(self, commit: bool = True) -> "Bundle":
        """Save the bundle and create in API if it has datasets but no API ID."""
        # Use the standard save behavior first. This handles new/existing objects
        # and m2m relations if commit=True.
        bundle: Bundle = super().save(commit=commit)

        # If commit=True, and the bundle now has datasets but hasn't been created
        # in the API yet, create it now.
        if (
            commit
            and self._has_datasets()
            and not bundle.bundle_api_id
            and getattr(settings, "ONS_BUNDLE_API_ENABLED", False)
        ):
            client = BundleAPIClient()
            try:
                bundle_data = _build_bundle_data_for_api(bundle)
                response = client.create_bundle(bundle_data)

                if "id" in response:
                    bundle.bundle_api_id = response["id"]
                    bundle.save(update_fields=["bundle_api_id"])
                    logger.info("Created bundle %s in Dataset API with ID: %s", bundle.pk, bundle.bundle_api_id)
                else:
                    logger.warning("Bundle %s created in API but no ID returned", bundle.pk)

            except BundleAPIClientError as e:
                logger.error("Failed to create bundle %s in Dataset API: %s", bundle.pk, e)
                # Don't raise the exception to avoid breaking the admin interface
                # The bundle will still be saved locally

        return bundle
