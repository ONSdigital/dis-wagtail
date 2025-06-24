import re
from typing import TYPE_CHECKING, Any, Optional

from django import forms
from django.utils.html import format_html
from wagtail.admin import widgets

if TYPE_CHECKING:
    from django.utils.safestring import SafeString

date_widget = widgets.AdminDateInput(attrs={"placeholder": "YYYY-MM-DD"})

datetime_widget = widgets.AdminDateTimeInput(attrs={"placeholder": "YYYY-MM-DD HH:MM"})


class ReadOnlyRichTextWidget(forms.Widget):
    def render(self, name: str, value: Optional[str], attrs: Any = None, renderer: Any = None) -> "SafeString":
        if value is None:
            value = ""
        # Remove HTML tags (note that there is no risk of XSS here as the value
        # is rendered as plain text in a disabled textarea)
        value = re.sub("<[^<]+?>", "", value)
        return format_html(
            "<textarea name={} disabled>{}</textarea>",
            name,
            value,
        )
