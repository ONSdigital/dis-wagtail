from django.apps import AppConfig


class ReleaseCalendarConfig(AppConfig):
    """The release calendar app config."""

    default_auto_field = "django.db.models.AutoField"
    name = "cms.release_calendar"

    def ready(self) -> None:
        import cms.release_calendar.signal_handlers  # noqa  # pylint: disable=unused-import,import-outside-toplevel
