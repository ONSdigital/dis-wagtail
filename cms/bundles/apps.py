from django.apps import AppConfig


class BundlesAppConfig(AppConfig):
    """The bundles app config."""

    default_auto_field = "django.db.models.AutoField"
    name = "cms.bundles"

    def ready(self):
        import cms.bundles.signal_handlers  # noqa # pylint: disable=unused-import, import-outside-toplevel
