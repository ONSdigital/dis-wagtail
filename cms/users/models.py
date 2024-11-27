from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):  # type: ignore[django-manager-missing]
    """Barebones custom user model."""

    teams = models.ManyToManyField("teams.Team", related_name="users", blank=True)
