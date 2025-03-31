from django.utils.dateformat import DateFormat

CONSTANT_VAR = 11


class CustomDateFormat(DateFormat):
    def a(self):
        if self.data.hour > CONSTANT_VAR:
            return "pm"
        return "am"


def custom_date_format(value, format_string):
    formatter = CustomDateFormat(value)
    return formatter.format(format_string)
