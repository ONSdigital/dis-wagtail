from datetime import datetime
from typing import Any

from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _
from wagtail.admin.forms import WagtailAdminPageForm
from wagtail.models import Locale

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

        if status == ReleaseStatus.CANCELLED and not cleaned_data.get("notice"):
            raise ValidationError({"notice": _("The notice field is required when the release is cancelled")})

        if status in [ReleaseStatus.CONFIRMED, ReleaseStatus.PUBLISHED]:
            if not cleaned_data.get("release_date"):
                raise ValidationError(
                    {"release_date": _("The release date field is required when the release is confirmed")}
                )

            if (
                self.instance.release_date
                and self.instance.release_date != cleaned_data.get("release_date")
                and len(self.instance.changes_to_release_date) == len(cleaned_data.get("changes_to_release_date", []))
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

        if (
            cleaned_data.get("release_date")
            and cleaned_data.get("next_release_date")
            and cleaned_data["release_date"] >= cleaned_data["next_release_date"]
        ):
            raise ValidationError({"next_release_date": _("The next release date must be after the release date.")})

        release_date_text = cleaned_data.get("release_date_text")
        if cleaned_data.get("release_date") and release_date_text:
            error = _("Please enter the release date or the release date text, not both.")
            raise ValidationError({"release_date": error, "release_date_text": error})

        if cleaned_data.get("next_release_date") and cleaned_data.get("next_release_text"):
            error = _("Please enter the next release date or the next release text, not both.")
            raise ValidationError({"next_release_date": error, "next_release_text": error})

        # TODO: expand to validate for non-English locales when adding multi-language.
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
                    raise ValidationError({"release_date_text": _("The end month must be after the start month.")})

        except ValueError:
            raise ValidationError(
                {
                    "release_date_text": _(
                        "The release date text must be in the 'Month YYYY' or 'Month YYYY to Month YYYY' format."
                    )
                }
            ) from None
