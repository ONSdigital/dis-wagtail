from django.apps import AppConfig


class ReleaseCalendarConfig(AppConfig):
    """The release calendar app config."""

    default_auto_field = "django.db.models.AutoField"
    name = "cms.release_calendar"

    def ready(self) -> None:
        """Import signal handlers when the app is ready."""
        from . import signal_handlers  # noqa: F401 # pylint: disable=import-outside-toplevel,unused-import
