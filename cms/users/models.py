from django.contrib.auth.models import AbstractUser


class User(AbstractUser):  # type: ignore[django-manager-missing]
    """Barebones custom user model."""
