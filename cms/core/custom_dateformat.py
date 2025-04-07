# Override the default date format to use am/ pm instead of a.m./ p.m.
from datetime import datetime, time

from django.utils.dateformat import DateFormat

# Custom date format class that overrides the default date format to use am/pm instead of a.m./p.m.

PM_TIME = 11


class NewDateFormat(DateFormat):
    def a(self) -> str:
        """Am or pm."""
        # To fix error: Item "date" of "date | time" has no attribute "hour"
        if isinstance(self.data, datetime | time):
            return "pm" if self.data.hour > PM_TIME else "am"
        return ""


def new_date_format(value: datetime, format_string: str) -> str:
    new_formatter = NewDateFormat(value)
    return new_formatter.format(format_string)
