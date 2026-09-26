from django.apps import AppConfig


class BundlesAppConfig(AppConfig):
    """The bundles app config."""

    default_auto_field = "django.db.models.AutoField"
    name = "cms.bundles"

    def ready(self) -> None:
        from .signal_handlers import register_signal_handlers  # pylint: disable=import-outside-toplevel

        register_signal_handlers()
