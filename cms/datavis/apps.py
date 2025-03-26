from django.apps import AppConfig


class DataVisConfig(AppConfig):
    default_auto_field = "django.db.models.AutoField"
    name = "cms.datavis"

    def ready(self):
        from . import checks  # noqa pylint: disable=import-outside-toplevel,unused-import
