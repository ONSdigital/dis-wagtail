from datetime import datetime, time

from django.utils.dateformat import DateFormat
from django.utils.formats import get_format

PM_TIME = 11


class ONSDateFormat(DateFormat):
    def a(self) -> str:
        """Am or pm."""
        if isinstance(self.data, datetime | time):
            return "pm" if self.data.hour > PM_TIME else "am"
        return ""


def ons_date_format(value: datetime, format_string: str) -> str:
    new_formatter = ONSDateFormat(value)
    return new_formatter.format(get_format(format_string))
