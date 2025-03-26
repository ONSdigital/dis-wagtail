from django.apps import AppConfig


class SearchConfig(AppConfig):
    name = "cms.search"

    def ready(self) -> None:
        import cms.search.checks  # pylint: disable=unused-import, import-outside-toplevel
        import cms.search.signals  # noqa # pylint: disable=unused-import, import-outside-toplevel
