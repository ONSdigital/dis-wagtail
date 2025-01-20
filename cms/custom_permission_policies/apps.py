from django.apps import AppConfig


class CustomPermissionPoliciesConfig(AppConfig):
    default_auto_field = "django.db.models.AutoField"
    name = "cms.custom_permission_policies"

    def ready(self) -> None:
        from .signal_handlers import register_signal_handlers  # pylint: disable=import-outside-toplevel

        register_signal_handlers()
