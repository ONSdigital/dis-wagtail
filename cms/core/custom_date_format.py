from datetime import datetime

from django.utils.dateformat import DateFormat
from django.utils.formats import get_format


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


def ons_date_format(value: datetime, format_string: str) -> str:
    return ONSDateFormat(value).format(get_format(format_string))
