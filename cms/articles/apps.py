from django.apps import AppConfig


class ArticlesConfig(AppConfig):
    default_auto_field = "django.db.models.AutoField"
    name = "cms.articles"

    def ready(self):
        import cms.articles.signals  # noqa  # pylint: disable=unused-import,import-outside-toplevel
