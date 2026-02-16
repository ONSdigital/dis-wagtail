from django.apps import AppConfig

from .signal_handlers import register_signal_handlers


class FrontendCacheAppConfig(AppConfig):
    name = "cms.frontend_cache"

    def ready(self) -> None:
        register_signal_handlers()
