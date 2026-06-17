from django.apps import AppConfig


class StandardPagesConfig(AppConfig):
    """The standard_pages app config."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "cms.standard_pages"

    def ready(self) -> None:
        from . import checks  # noqa: F401 # pylint: disable=unused-import, import-outside-toplevel
