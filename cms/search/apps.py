from django.apps import AppConfig


class SearchConfig(AppConfig):
    name = "cms.search"

    def ready(self) -> None:
        import cms.search.checks  # pylint: disable=unused-import, import-outside-toplevel
        import cms.search.signal_handlers  # noqa # pylint: disable=unused-import, import-outside-toplevel
        from cms.search.signal_handlers import connect_page_delete_signal  # pylint: disable=import-outside-toplevel

        connect_page_delete_signal()
