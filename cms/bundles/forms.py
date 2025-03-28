from typing import TYPE_CHECKING, Any

from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone
from wagtail.admin.forms import WagtailAdminModelForm

from cms.bundles.enums import ACTIVE_BUNDLE_STATUS_CHOICES, EDITABLE_BUNDLE_STATUSES, BundleStatus

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
            for field_name in self.fields:
                if field_name != "status":
                    self.fields[field_name].disabled = True

        # fully hide and disable the approved_at/by fields to prevent form tampering
        self.fields["approved_at"].disabled = True
        self.fields["approved_at"].widget = forms.HiddenInput()
        self.fields["approved_by"].disabled = True
        self.fields["approved_by"].widget = forms.HiddenInput()

        self.original_status = self.instance.status

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

    def clean(self) -> dict[str, Any] | None:
        """Validates the form.

        - the bundle cannot be self-approved. That is, someone other than the bundle creator must approve it.
        - tidies up/ populates approved at/by
        """
        cleaned_data: dict[str, Any] = super().clean()

        self._validate_bundled_pages()

        status = cleaned_data["status"]
        if self.instance.status != status:
            # the status has changed, let's check
            if status == BundleStatus.APPROVED:
                if self.instance.created_by_id == self.for_user.pk:
                    cleaned_data["status"] = self.instance.status
                    self.add_error("status", ValidationError("You cannot self-approve your own bundle!"))
                else:
                    # the approver is different from the creator, so let's populate the relevant fields.
                    cleaned_data["approved_at"] = timezone.now()
                    cleaned_data["approved_by"] = self.for_user
            elif self.instance.status == BundleStatus.APPROVED:
                cleaned_data["approved_at"] = None
                cleaned_data["approved_by"] = None

        if self.cleaned_data["release_calendar_page"] and self.cleaned_data["publication_date"]:
            error = "You must choose either a Release Calendar page or a Publication date, not both."
            self.add_error("release_calendar_page", error)
            self.add_error("publication_date", error)

        return cleaned_data
