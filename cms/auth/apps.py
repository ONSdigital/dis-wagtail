from django.apps import AppConfig


class AuthConfig(AppConfig):
    default_auto_field = "django.db.models.AutoField"
    name = "cms.auth"
    label = "ons_auth"

    def ready(self) -> None:
        import cms.auth.checks  # noqa: F401  # pylint: disable=unused-import, import-outside-toplevel
