from django.apps import AppConfig


class FrontendCacheAppConfig(AppConfig):
    name = "cms.frontend_cache"

    def ready(self) -> None:
        from .signal_handlers import register_signal_handlers  # pylint: disable=import-outside-toplevel

        register_signal_handlers()
