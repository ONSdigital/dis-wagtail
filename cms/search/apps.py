from django.apps import AppConfig


class SearchConfig(AppConfig):
    name = "cms.search"

    def ready(self) -> None:
        import cms.search.checks  # pylint: disable=unused-import, import-outside-toplevel
        import cms.search.signals  # noqa # pylint: disable=unused-import, import-outside-toplevel
        from cms.search.signals import connect_page_delete_signal  # pylint: disable=import-outside-toplevel

        connect_page_delete_signal()
