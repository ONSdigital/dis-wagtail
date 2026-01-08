from datetime import datetime
from typing import TYPE_CHECKING, Any

from django.core.exceptions import ValidationError
from django.urls import reverse
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from wagtail.admin.forms import WagtailAdminPageForm
from wagtail.blocks.stream_block import StreamValue
from wagtail.models import Locale

from cms.bundles.permissions import user_can_manage_bundles
from cms.core.widgets import ReadOnlyRichTextWidget
from cms.release_calendar.permissions import user_can_modify_notice

from .enums import LOCKED_STATUS_STATUSES, NON_PROVISIONAL_STATUS_CHOICES, ReleaseStatus
from .utils import get_translated_string, parse_day_month_year_time, parse_month_year

if TYPE_CHECKING:
    from .models import ReleaseCalendarPage

DATE_SEPARATOR = {
    "en": " to ",
    "cy": " i ",
}

MAX_DATE_PARTS = 2


class ReleaseCalendarPageAdminForm(WagtailAdminPageForm):
    """Convenience administrative form for easier calendar page data validation."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

        if not self.instance.pk:
            # Remove the field from the form as there's no previous release date to reference
            del self.fields["changes_to_release_date"]

        # Get the live version of the page for validation comparisons
        self.live_page: "ReleaseCalendarPage | None" = None  # noqa: UP037
        if self.instance and self.instance.pk:
            # Import at runtime to avoid circular import
            from .models import ReleaseCalendarPage  # pylint: disable=import-outside-toplevel

            self.live_page = (
                ReleaseCalendarPage.objects.filter(pk=self.instance.pk)
                .live()
                # Grab the fields we need for validation
                .only("release_date", "status", "changes_to_release_date")
                .first()
            )

        if self.instance.status != ReleaseStatus.PROVISIONAL:
            # Once a release calendar page is confirmed, it cannot go back to provisional
            self.fields["status"].choices = NON_PROVISIONAL_STATUS_CHOICES

        # Remove ReleaseStatus.PUBLISHED from the status choices.
        # Release Calendar pages should only ever move to the PUBLISHED status via a bundle.
        if self.instance.status != ReleaseStatus.PUBLISHED:
            self.fields["status"].choices = [
                choice for choice in self.fields["status"].choices if choice[0] != ReleaseStatus.PUBLISHED
            ]
        else:
            self.fields["release_date"].disabled = True
            self.fields["status"].disabled = True

        if self.instance.live_status in LOCKED_STATUS_STATUSES:
            # If the status is locked, disable the status field
            self.fields["status"].disabled = True

        if self.instance.live_notice and not user_can_modify_notice(self.for_user):
            self.fields["notice"].disabled = True
            self.fields["notice"].widget = ReadOnlyRichTextWidget()

    def clean(self) -> dict:
        """Validate the submitted release calendar data."""
        cleaned_data: dict = super().clean()

        status = cleaned_data.get("status", "")
        notice = cleaned_data.get("notice", "")
        self._validate_cancelled_status(status, notice)
        self._validate_non_provisional_status(status, cleaned_data)
        self._validate_change_logs(status, cleaned_data)
        self._validate_date_fields(cleaned_data)
        self._validate_text_fields(cleaned_data)

        return cleaned_data

    def _validate_cancelled_status(self, status: str, notice: str) -> None:
        """Validate cancelled status requirements."""
        if status == ReleaseStatus.CANCELLED:
            self._validate_not_in_active_bundle()
            if not notice:
                raise ValidationError({"notice": "The notice field is required when the release is cancelled"})

    def _validate_non_provisional_status(self, status: str, cleaned_data: dict) -> None:
        """Validate non-provisional status requirements."""
        if status != ReleaseStatus.PROVISIONAL:
            # Input field is hidden with custom JS for non-provisional releases,
            # set to None to avoid unexpected behavior
            cleaned_data["release_date_text"] = ""

    def _validate_change_logs(self, status: str, cleaned_data: dict) -> None:
        """Validate change log requirements."""
        live_release_date = self.live_page.release_date if self.live_page else None
        live_status = self.live_page.status if self.live_page else None
        new_changes = cleaned_data.get("changes_to_release_date", [])
        old_changes_count = len(self.live_page.changes_to_release_date) if self.live_page else 0
        new_changes_count = len(new_changes)
        added_changes_count = new_changes_count - old_changes_count

        date_has_changed = live_release_date is not None and live_release_date != cleaned_data.get("release_date")
        change_log_added = new_changes_count > old_changes_count

        if (
            status in [ReleaseStatus.CONFIRMED, ReleaseStatus.PUBLISHED]
            and self.live_page
            and live_status in [ReleaseStatus.CONFIRMED, ReleaseStatus.PUBLISHED]
        ):
            self._validate_change_logs_dates(date_has_changed, change_log_added)

        if added_changes_count > 1:
            raise ValidationError(
                {
                    "changes_to_release_date": (
                        "Only one 'Changes to release date' entry can be added per release date change."
                    )
                }
            )

    def _validate_date_fields(self, cleaned_data: dict) -> None:
        """Validate date field relationships."""
        if (
            cleaned_data.get("release_date")
            and cleaned_data.get("next_release_date")
            and cleaned_data["release_date"] >= cleaned_data["next_release_date"]
        ):
            raise ValidationError({"next_release_date": "The next release date must be after the release date."})

        if cleaned_data.get("next_release_date") and cleaned_data.get("next_release_date_text"):
            error = "Please enter the next release date or the next release text, not both."
            raise ValidationError({"next_release_date": error, "next_release_date_text": error})

    def _validate_text_fields(self, cleaned_data: dict) -> None:
        """Validate text field formats."""
        if release_date_text := cleaned_data.get("release_date_text"):
            self.validate_release_date_text_format(release_date_text, self.instance.locale)

        if next_release_date_text := cleaned_data.get("next_release_date_text"):
            locale_code = "en" if self.instance.locale.language_code == "en-gb" else self.instance.locale.language_code
            self.validate_release_next_date_text_format(next_release_date_text, locale_code, cleaned_data)

    def clean_notice(self) -> str:
        """Validate the notice field."""
        notice: str = self.cleaned_data.get("notice", "")

        if (
            self.instance.live_notice
            and notice != self.instance.live_notice
            and not user_can_modify_notice(self.for_user)
        ):
            self.add_error(
                "notice",
                ValidationError("You cannot remove or edit a published notice from a release calendar page."),
            )
            notice = self.instance.live_notice
        return notice

    def clean_changes_to_release_date(self) -> StreamValue:
        """Validate the changes_to_release_date field."""
        changes_to_release_date: StreamValue = self.cleaned_data["changes_to_release_date"]

        if self.instance.pk is None:
            return changes_to_release_date

        old_frozen_changes = [change for change in self.instance.changes_to_release_date if change.value["frozen"]]
        new_frozen_changes = [change for change in changes_to_release_date if change.value["frozen"]]

        # Check if any frozen changes are being removed or tampered with
        if len(old_frozen_changes) != len(new_frozen_changes):
            self.add_error(
                "changes_to_release_date",
                ValidationError(
                    "You cannot remove a release date change that has already been published. "
                    "Please refresh the page and try again."
                ),
            )

        return changes_to_release_date

    def validate_release_date_text_format(self, text: str, locale: Locale) -> None:
        """Validates that the release_date_text follows the locale-specific format."""
        # Normalize the locale code to a standard format
        locale_code = "en" if locale.language_code == "en-gb" else locale.language_code

        if locale_code not in DATE_SEPARATOR:
            raise NotImplementedError(f"Release date text validation not implemented for locale '{locale_code}'.")

        parts = text.split(DATE_SEPARATOR[locale_code], maxsplit=1)
        dates = [parse_month_year(part, locale_code) for part in parts]

        if any(date is None for date in dates) or len(dates) > MAX_DATE_PARTS:
            language = self.instance.locale.get_display_name()
            raise ValidationError(
                {
                    "release_date_text": (
                        "The release date text must be in the 'Month YYYY' or 'Month YYYY to Month YYYY' format"
                        f" in {language}."
                    )
                }
            )
        if len(dates) == MAX_DATE_PARTS and dates[0] >= dates[1]:  # type: ignore # Dates guaranteed to not be None
            raise ValidationError({"release_date_text": "The end month must be after the start month."})

    def validate_release_next_date_text_format(
        self, next_release_date_text: str, locale: str, cleaned_data: dict
    ) -> None:
        parsed_date = parse_day_month_year_time(next_release_date_text, locale)

        if parsed_date is not None and cleaned_data.get("release_date") and parsed_date <= cleaned_data["release_date"]:
            raise ValidationError({"next_release_date_text": "The next release date must be after the release date."})

        to_be_confirmed_text = get_translated_string(
            "To be confirmed",
            self.instance.locale.language_code,
        ) or _("To be confirmed")  # This line ensures makemessages picks up the string

        if parsed_date is None and to_be_confirmed_text != next_release_date_text:
            raise ValidationError(
                {
                    "next_release_date_text": (
                        'The next release date text must be in the "DD Month YYYY Time" format or say '
                        f'"{to_be_confirmed_text}" in {self.instance.locale.get_display_name()}.'
                    )
                }
            )

    def _validate_not_in_active_bundle(self) -> None:
        """Prevent cancellation when the page is part of any active bundle."""
        bundle = self.instance.active_bundle
        if not bundle:
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
            "This release calendar page is linked to bundle '{}'. "
            "Please unlink the release calendar page from the bundle before cancelling.",
            bundle_str,
        )
        raise ValidationError({"status": message})

    def _validate_change_logs_dates(self, date_has_changed: bool, change_log_added: bool) -> None:
        if date_has_changed and not change_log_added:
            raise ValidationError(
                {
                    "changes_to_release_date": (
                        "If a confirmed calendar entry needs to be rescheduled, "
                        "the 'Changes to release date' field must be filled out."
                    )
                }
            )

        if change_log_added and not date_has_changed:
            raise ValidationError(
                {
                    "changes_to_release_date": (
                        "You have added a 'Changes to release date' entry, "
                        "but the release date is the same as the published version."
                    )
                }
            )

    def clean_release_date(self) -> datetime | None:
        # Set seconds to 0 to make scheduling less surprising
        if release_date := self.cleaned_data["release_date"]:
            return release_date.replace(second=0)  # type: ignore[no-any-return]
        return None
