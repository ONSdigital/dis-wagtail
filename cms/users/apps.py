from django.apps import AppConfig


class UsersConfig(AppConfig):
    """The users app config."""

    default_auto_field = "django.db.models.AutoField"
    name = "cms.users"
    label = "users"
