from datetime import datetime
from typing import Any

from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _
from wagtail.admin.forms import WagtailAdminPageForm

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

        status = cleaned_data["status"]

        if status == ReleaseStatus.CANCELLED and not cleaned_data["notice"]:
            raise ValidationError({"notice": _("The notice field is required when the release is cancelled")})

        if status in [ReleaseStatus.CONFIRMED, ReleaseStatus.PUBLISHED]:
            if not cleaned_data["release_date"]:
                raise ValidationError(
                    {"release_date": _("The release date field is required when the release is confirmed")}
                )

            if (
                self.instance.release_date
                and self.instance.release_date != cleaned_data["release_date"]
                and len(self.instance.changes_to_release_date) == len(cleaned_data["changes_to_release_date"])
            ):
                # A change in the release date requires updating changes_to_release_date
                raise ValidationError(
                    {
                        "changes_to_release_date": _(
                            "If a confirmed calendar entry needs to be rescheduled, "
                            "the 'Changes to release date' field must be filled out."
                        )
                    }
                )

            if len(self.instance.changes_to_release_date) > len(cleaned_data["changes_to_release_date"]):
                raise ValidationError(
                    {"changes_to_release_date": _("You cannot remove entries from the 'Changes to release date'.")}
                )

        if cleaned_data["release_date_text"]:
            self.validate_release_date_text_format(cleaned_data["release_date_text"])

        return cleaned_data

    def validate_release_date_text_format(self, text: str) -> None:
        """Validates that the release_date_text follows the Month YYYY, or Month YYYY to Month YYYY format."""
        parts = text.split(" to ", maxsplit=1)

        try:
            date_from = datetime.strptime(parts[0], "%B %Y")
            if len(parts) > 1:
                date_to = datetime.strptime(parts[1], "%B %Y")
                if date_from >= date_to:
                    raise ValidationError({"release_date_text": _("The end month must be after the start month.")})

        except ValueError:
            raise ValidationError(
                {
                    "release_date_text": _(
                        "The release date text must be in the 'Month YYYY' or 'Month YYYY to Month YYYY' format."
                    )
                }
            ) from None
