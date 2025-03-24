from django.apps import AppConfig


class SearchConfig(AppConfig):
    name = "cms.search"

    def ready(self):
        import cms.search.checks
