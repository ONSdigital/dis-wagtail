from django.apps import AppConfig


class ImagesConfig(AppConfig):
    """The images app config."""

    default_auto_field = "django.db.models.AutoField"
    name = "cms.images"

    def ready(self) -> None:
        from . import signal_handlers  # noqa pylint: disable=import-outside-toplevel,unused-import
