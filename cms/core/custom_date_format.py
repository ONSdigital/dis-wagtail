from datetime import date, datetime, time

from django.utils.dateformat import DateFormat
from django.utils.formats import get_format
from django.utils.timezone import is_aware, localtime


class ONSDateFormat(DateFormat):
    """We override the default 'a.m.' and 'p.m.' in the 'a' method from the
    TimeFormat class (which is inherited by DateFormat) class so we can remove the '.'
    so it becomes 'am' and 'pm' instead.
    """

    # This is the cutoff hour for AM/PM. If the hour is greater than or equal to this
    PM_CUTOFF_HOUR = 11

    def a(self) -> str:
        if isinstance(self.data, datetime):
            return "pm" if self.data.hour > self.PM_CUTOFF_HOUR else "am"
        return ""


def ons_date_format(value: date | datetime, format_string: str) -> str:
    # ensure the value uses the configured timezone
    if isinstance(value, datetime) and is_aware(value):
        value = localtime(value)
    formatted_date = ONSDateFormat(value).format(get_format(format_string))

    # Note: Django currently has a typo in the Welsh translation for "July" (Gorffenaf instead of Gorffennaf).
    # This is a temporary fix to correct the typo in the date format.
    # TODO: Once the Django translation is fixed, this can be removed.
    # Reference:
    # https://github.com/django/django/blob/c1fa3fdd040718356e5a3b9a0fe699d73f47a940/django/conf/locale/cy/LC_MESSAGES/django.po#L926
    return formatted_date.replace("Gorffenaf", "Gorffennaf")


def ons_default_datetime() -> datetime:
    """Returns today's date at 9:30am."""
    return datetime.combine(date.today(), time(9, 30))
