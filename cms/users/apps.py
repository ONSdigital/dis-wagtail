from django.apps import AppConfig


class UsersConfig(AppConfig):
    """The users app config."""

    default_auto_field = "django.db.models.AutoField"
    name = "cms.users"
    label = "users"

    def ready(self) -> None:
        from . import signal_handlers  # noqa  # pylint: disable=unused-import,import-outside-toplevel
