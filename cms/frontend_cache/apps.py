from django.apps import AppConfig


class FrontendCacheAppConfig(AppConfig):
    name = "cms.frontend_cache"

    def ready(self) -> None:
        from .signal_handlers import (  # pylint: disable=import-outside-toplevel
            disconnect_signal_handlers,
            register_signal_handlers,
        )

        # we disconnect the core front-end cache signal handles as we handle them
        # with specific logic
        disconnect_signal_handlers()
        register_signal_handlers()
