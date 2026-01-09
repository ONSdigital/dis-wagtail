import re
from typing import TYPE_CHECKING, Any

from django import forms
from django.utils.html import format_html
from wagtail.admin import widgets
from wagtail.admin.telepath import register
from wagtail.admin.widgets.datetime import AdminDateTimeInput, AdminDateTimeInputAdapter

if TYPE_CHECKING:
    from django.utils.safestring import SafeString

date_widget = widgets.AdminDateInput(attrs={"placeholder": "YYYY-MM-DD"})


class ONSAdminDateTimeInput(AdminDateTimeInput):
    """Updates DateTime input with a placeholder and changes time selection intervals to 30 minutes."""

    def __init__(
        self,
        attrs: dict | None = None,
        date_format: str | None = None,
        time_format: str | None = None,
        js_overlay_parent_selector: str = "body",
    ):
        if attrs is None:
            attrs = {}
        attrs.setdefault("placeholder", "YYYY-MM-DD HH:MM")

        super().__init__(
            attrs=attrs,
            format=date_format,
            time_format=time_format,
            js_overlay_parent_selector=js_overlay_parent_selector,
        )

    def get_config(self) -> Any:
        config = super().get_config()
        config.update({"step": 30})

        return config


register(AdminDateTimeInputAdapter(), ONSAdminDateTimeInput)


class ReadOnlyRichTextWidget(forms.Widget):
    def render(self, name: str, value: str | None, attrs: Any = None, renderer: Any = None) -> SafeString:
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
