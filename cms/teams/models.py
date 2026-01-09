from typing import ClassVar

from django.db import models
from django.utils import timezone
from django.utils.functional import cached_property
from wagtail.admin.utils import get_user_display_name
from wagtail.search import index


class TeamQuerySet(models.QuerySet["Team"]):
    def active(self) -> TeamQuerySet:
        """Returns only active teams."""
        return self.filter(is_active=True)


class TeamManager(models.Manager.from_queryset(TeamQuerySet)):  # type: ignore[misc]
    pass


class Team(index.Indexed, models.Model):  # type: ignore[django-manager-missing]
    identifier = models.CharField(max_length=255, unique=True)
    name = models.CharField(max_length=255)
    precedence = models.PositiveIntegerField(null=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(default=timezone.now)
    is_active = models.BooleanField(default=True)

    objects: TeamManager = TeamManager()

    search_fields: ClassVar[list[index.BaseField]] = [
        index.SearchField("name"),
        index.AutocompleteField("name"),
        index.FilterField("is_active"),
    ]

    class Meta:
        ordering: ClassVar[list[str]] = ["-is_active", "precedence", "name"]

    def __str__(self) -> str:
        return self.name

    @cached_property
    def get_users_display(self) -> str:
        """Return a comma separated list of users in the team."""
        return ", ".join(
            get_user_display_name(user) for user in self.users.all().only("first_name", "last_name", "username")
        )
