from typing import Any

from wagtail.admin import widgets
from wagtail.admin.widgets.datetime import AdminDateTimeInput, AdminDateTimeInputAdapter
from wagtail.telepath import register

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
