from django.apps import AppConfig


class ArticlesConfig(AppConfig):
    default_auto_field = "django.db.models.AutoField"
    name = "cms.articles"

    def ready(self) -> None:
        import cms.articles.signal_handlers  # noqa  # pylint: disable=unused-import,import-outside-toplevel
