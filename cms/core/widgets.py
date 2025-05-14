from wagtail.admin import widgets
from wagtail.admin.widgets.datetime import AdminDateTimeInput, AdminDateTimeInputAdapter
from wagtail.telepath import register

date_widget = widgets.AdminDateInput(attrs={"placeholder": "YYYY-MM-DD"})


# Change release date time step to 30 minutes
class ONSAdminDateTimeInput(AdminDateTimeInput):
    def __init__(
        self,
        attrs: dict | None = None,
        format: str | None = None,
        time_format: str | None = None,
        js_overlay_parent_selector: str = "body",
    ):
        if attrs is None:
            attrs = {}
        attrs.setdefault("placeholder", "YYYY-MM-DD HH:MM")

        super().__init__(
            attrs=attrs, format=format, time_format=time_format, js_overlay_parent_selector=js_overlay_parent_selector
        )

    def get_config(self):
        config = super().get_config()
        # Change step to (30 minutes)
        config.update({"step": 30})

        return config


register(AdminDateTimeInputAdapter(), ONSAdminDateTimeInput)
