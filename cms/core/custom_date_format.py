from datetime import datetime

from django.utils.dateformat import DateFormat
from django.utils.formats import get_format

PM_TIME = 11


class ONSDateFormat(DateFormat):
    def a(self) -> str:
        """We override the default 'a.m.' and 'p.m.' in the 'a' method from the
        TimeFormat class (which is inherited by DateFormat) class so we can remove remove the '.'
        so it becomes 'am' and 'pm' instead.
        """
        if isinstance(self.data, datetime):
            return "pm" if self.data.hour > PM_TIME else "am"
        return ""


def ons_date_format(value: datetime, format_string: str) -> str:
    new_formatter = ONSDateFormat(value)
    return new_formatter.format(get_format(format_string))
