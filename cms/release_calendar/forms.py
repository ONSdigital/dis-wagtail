from datetime import datetime
from typing import Any

from django.core.exceptions import ValidationError
from django.urls import reverse
from django.utils.html import format_html
from wagtail.admin.forms import WagtailAdminPageForm
from wagtail.blocks.stream_block import StreamValue
from wagtail.models import Locale, PageLogEntry

from cms.bundles.permissions import user_can_manage_bundles

from .enums import NON_PROVISIONAL_STATUS_CHOICES, ReleaseStatus


class ReleaseCalendarPageAdminForm(WagtailAdminPageForm):
    """Convenience administrative form for easier calendar page data validation."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

        if self.instance.status != ReleaseStatus.PROVISIONAL:
            # Once a release calendar page is confirmed, it cannot go back to provisional
            self.fields["status"].choices = NON_PROVISIONAL_STATUS_CHOICES

        if self.instance.status == ReleaseStatus.PUBLISHED:
            self.fields["release_date"].disabled = True

    def clean(self) -> dict:
        """Validate the submitted release calendar data."""
        cleaned_data: dict = super().clean()

        status = cleaned_data.get("status")

        if status == ReleaseStatus.CANCELLED:
            if not cleaned_data.get("notice"):
                raise ValidationError({"notice": "The notice field is required when the release is cancelled"})

            self.validate_bundle_not_pending_publication(status)

        if status != ReleaseStatus.PROVISIONAL:
            # Input field is hidden with custom JS for non-provisional releases,
            # set to None to avoid unexpected behavior
            cleaned_data["release_date_text"] = ""

        if (
            status in [ReleaseStatus.CONFIRMED, ReleaseStatus.PUBLISHED]
            and self.instance.release_date
            and self.instance.release_date != cleaned_data.get("release_date")
            and len(self.instance.changes_to_release_date) == len(cleaned_data.get("changes_to_release_date", []))
        ):
            # A change in the release date requires updating changes_to_release_date
            raise ValidationError(
                {
                    "changes_to_release_date": (
                        "If a confirmed calendar entry needs to be rescheduled, "
                        "the 'Changes to release date' field must be filled out."
                    )
                }
            )

        if (
            cleaned_data.get("release_date")
            and cleaned_data.get("next_release_date")
            and cleaned_data["release_date"] >= cleaned_data["next_release_date"]
        ):
            raise ValidationError({"next_release_date": "The next release date must be after the release date."})

        if cleaned_data.get("next_release_date") and cleaned_data.get("next_release_date_text"):
            error = "Please enter the next release date or the next release text, not both."
            raise ValidationError({"next_release_date": error, "next_release_date_text": error})

        # TODO: expand to validate for non-English locales when adding multi-language.
        release_date_text = cleaned_data.get("release_date_text")
        if release_date_text and self.instance.locale_id == Locale.get_default().pk:
            self.validate_english_release_date_text_format(release_date_text)

        return cleaned_data

    def validate_english_release_date_text_format(self, text: str) -> None:
        """Validates that the release_date_text follows the Month YYYY, or Month YYYY to Month YYYY format."""
        parts = text.split(" to ", maxsplit=1)

        try:
            date_from = datetime.strptime(parts[0], "%B %Y")
            if len(parts) > 1:
                date_to = datetime.strptime(parts[1], "%B %Y")
                if date_from >= date_to:
                    raise ValidationError({"release_date_text": "The end month must be after the start month."})

        except ValueError:
            raise ValidationError(
                {
                    "release_date_text": (
                        "The release date text must be in the 'Month YYYY' or 'Month YYYY to Month YYYY' format."
                    )
                }
            ) from None

    def validate_bundle_not_pending_publication(self, status: str) -> None:
        if self.instance.status == status:
            return

        bundle = self.instance.active_bundle
        if not (bundle and bundle.is_ready_to_be_published):
            return

        if self.for_user and user_can_manage_bundles(self.for_user):
            bundle_str = format_html(
                '<a href="{}" target="_blank" title="Manage bundle">{}</a>',
                reverse("bundle:edit", args=[bundle.pk]),
                bundle.name,
            )
        else:
            bundle_str = bundle.name

        message = format_html(
            "This release calendar page is linked to bundle '{}' which is ready to be published. "
            "Please unschedule the bundle and unlink the release calendar page before making the cancellation.",
            bundle_str,
        )
        raise ValidationError({"status": message})

    def clean_changes_to_release_date(self) -> StreamValue:  # noqa: C901
        changes_to_release_date: StreamValue = self.cleaned_data["changes_to_release_date"]

        if self.instance.pk is None:
            if changes_to_release_date:
                self.add_error(
                    "changes_to_release_date",
                    ValidationError(
                        "You cannot create change to release date for a page that has not been published yet"
                    ),
                )
            return changes_to_release_date

        old_frozen_versions = [
            date_change_log.value["version_id"]
            for date_change_log in self.instance.changes_to_release_date
            if date_change_log.value["frozen"]
        ]
        new_frozen_versions = [
            date_change_log.value["version_id"]
            for date_change_log in changes_to_release_date
            if date_change_log.value["frozen"]
        ]

        latest_frozen_date = max(
            (
                date_change_log.value["previous_date"]
                for date_change_log in changes_to_release_date
                if date_change_log.value["frozen"]
            ),
            default=None,
        )

        if old_frozen_versions != new_frozen_versions:
            self.add_error(
                "changes_to_release_date",
                ValidationError(
                    "You cannot remove a change to release date that has already been published. "
                    "Please refresh the page and try again."
                ),
            )

        latest_published_revision_id = (
            PageLogEntry.objects.filter(page=self.instance, action="wagtail.publish")
            .order_by("-timestamp")
            .values_list("revision_id", flat=True)
            .first()
        )

        if changes_to_release_date and not latest_published_revision_id:
            self.add_error(
                "changes_to_release_date",
                ValidationError(
                    "You cannot create a change to release date for a page that has not been published yet"
                ),
            )

        new_date_change_log = None
        latest_date_change_log_version = 0

        for date_change_log in changes_to_release_date:
            if not date_change_log.value["frozen"]:
                if new_date_change_log:
                    self.add_error(
                        "changes_to_release_date",
                        ValidationError("Only one new change to release date can be published at a time"),
                    )
                    break
                new_date_change_log = date_change_log
                if latest_frozen_date and date_change_log.value["previous_date"] < latest_frozen_date:
                    self.add_error(
                        "changes_to_release_date",
                        ValidationError(
                            "You cannot create a change to release date with a date earlier than the latest change"
                        ),
                    )
            latest_date_change_log_version = max(
                latest_date_change_log_version, date_change_log.value["version_id"] or 0
            )

        if new_date_change_log:
            if not new_date_change_log.value["version_id"]:
                new_date_change_log.value["version_id"] = latest_date_change_log_version + 1
            if not new_date_change_log.value["version_id"]:
                new_date_change_log.value["version_id"] = latest_published_revision_id

        sorted_changes = sorted(
            changes_to_release_date,
            key=lambda change: change.value["previous_date"],
            reverse=True,
        )

        return StreamValue(changes_to_release_date.stream_block, sorted_changes)
