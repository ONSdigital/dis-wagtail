from django.apps import AppConfig


class MethodologyConfig(AppConfig):
    default_auto_field = "django.db.models.AutoField"
    name = "cms.methodology"

    def ready(self) -> None:
        import cms.methodology.signal_handlers  # noqa # pylint: disable=unused-import, import-outside-toplevel
