from django.apps import AppConfig


class PrivateMediaConfig(AppConfig):
    default_auto_field = "django.db.models.AutoField"
    name = "cms.private_media"

    def ready(self) -> None:
        from .signal_handlers import register_signal_handlers  # type: ignore[import-outside-toplevel]

        register_signal_handlers()
