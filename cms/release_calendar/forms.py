from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _
from wagtail.admin.forms import WagtailAdminPageForm

from .enums import ReleaseStatus


class ReleaseCalendarPageAdminForm(WagtailAdminPageForm):
    """Convenience administrative form for easier calendar page data validation."""

    def clean(self) -> dict:
        """Validate the submitted release calendar data."""
        cleaned_data = super().clean()

        if cleaned_data["status"] == ReleaseStatus.CANCELLED and not cleaned_data["notice"]:
            raise ValidationError({"notice": _("The notice field is required when the release is cancelled")})

        return cleaned_data
