from django.apps import AppConfig


class NavigationConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "cms.navigation"

    def ready(self) -> None:
        from .signal_handlers import register_signal_handlers  # pylint: disable=import-outside-toplevel

        register_signal_handlers()
