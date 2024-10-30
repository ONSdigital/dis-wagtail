from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _
from wagtail.admin.forms import WagtailAdminPageForm

from .enums import NON_PROVISIONAL_STATUS_CHOICES, ReleaseStatus


class ReleaseCalendarPageAdminForm(WagtailAdminPageForm):
    """Convenience administrative form for easier calendar page data validation."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.instance.status != ReleaseStatus.PROVISIONAL:
            # Once a release calendar page is confirmed, it cannot go back to provisional
            self.fields["status"].choices = NON_PROVISIONAL_STATUS_CHOICES

        if self.instance.status == ReleaseStatus.PUBLISHED:
            self.fields["release_date"].disabled = True

    def clean(self) -> dict:
        """Validate the submitted release calendar data."""
        cleaned_data = super().clean()

        status = cleaned_data["status"]

        if status == ReleaseStatus.CANCELLED and not cleaned_data["notice"]:
            raise ValidationError({"notice": _("The notice field is required when the release is cancelled")})

        if status in [ReleaseStatus.CONFIRMED, ReleaseStatus.PUBLISHED]:
            if not cleaned_data["release_date"]:
                raise ValidationError(
                    {"release_date": _("The release date field is required when the release is confirmed")}
                )

            if self.instance.release_date != cleaned_data["release_date"] and len(
                self.instance.changes_to_release_date
            ) == len(cleaned_data["changes_to_release_date"]):
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

        return cleaned_data
