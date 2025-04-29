from django.db.models.fields import DateTimeField
from wagtail.admin import widgets


class DatePlaceholder(DateTimeField):
    """A placeholder for a date field."""

    date_widget = widgets.AdminDateInput(
        attrs={
            "placeholder": "YYYY-MM-DD",
        },
    )

    datetime_widget = widgets.AdminDateTimeInput(
        attrs={
            "placeholder": "YYYY-MM-DD HH:MM",
        },
    )
