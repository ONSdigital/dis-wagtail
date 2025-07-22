from django.apps import AppConfig


class SearchConfig(AppConfig):
    name = "cms.search"

    def ready(self) -> None:
        from . import checks, signal_handlers  # noqa: F401 # pylint: disable=unused-import, import-outside-toplevel
