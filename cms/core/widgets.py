from wagtail.admin import widgets

date_widget = widgets.AdminDateInput(attrs={"placeholder": "YYYY-MM-DD"})

datetime_widget = widgets.AdminDateTimeInput(attrs={"placeholder": "YYYY-MM-DD HH:MM"})
