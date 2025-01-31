from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.functional import cached_property


class User(AbstractUser):  # type: ignore[django-manager-missing]
    """Barebones custom user model."""

    teams = models.ManyToManyField("teams.Team", related_name="users", blank=True)

    @cached_property
    def active_team_ids(self) -> list[int]:
        return list(self.teams.filter(is_active=True).values_list("pk", flat=True))
