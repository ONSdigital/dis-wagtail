from django.apps import AppConfig


class CoreConfig(AppConfig):
    """The core app config."""

    default_auto_field = "django.db.models.AutoField"
    name = "cms.core"
    label = "core"

    def ready(self) -> None:
        from . import audit  # noqa pylint: disable=import-outside-toplevel,unused-import
