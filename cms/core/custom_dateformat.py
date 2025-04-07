# Override the default date format to use am/ pm instead of a.m./ p.m.
from datetime import datetime

from django.utils.dateformat import DateFormat

# Custom date format class that overrides the default date format to use am/pm instead of a.m./p.m.

PM_TIME = 11


class NewDateFormat(DateFormat):
    def a(self) -> str:
        """Am or pm."""
        if self.data.hour > PM_TIME:
            return "pm"
        return "am"


def new_date_format(value: datetime, format_string: str) -> str:
    new_formatter = NewDateFormat(value)
    return new_formatter.format(format_string)
