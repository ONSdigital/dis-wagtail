from django.apps import AppConfig


class CoreConfig(AppConfig):
    """The core app config."""

    default_auto_field = "django.db.models.AutoField"
    name = "cms.core"
    label = "core"

    def ready(self) -> None:
        from . import checks  # noqa pylint: disable=import-outside-toplevel,unused-import

        # TODO: remove when upgrading to Wagtail 7.0
        import cms.core.monkey_patches  # noqa pylint: disable=unused-import,import-outside-toplevel
