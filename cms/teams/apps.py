from django.apps import AppConfig


class TeamsConfig(AppConfig):
    """The teams app config."""

    default_auto_field = "django.db.models.AutoField"
    name = "cms.teams"

    def ready(self) -> None:
        import cms.teams.checks  # noqa: F401  # pylint: disable=unused-import, import-outside-toplevel
