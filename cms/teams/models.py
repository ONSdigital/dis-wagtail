from functools import cached_property
from typing import ClassVar

from django.db import models
from django.utils import timezone
from wagtail.admin.utils import get_user_display_name
from wagtail.search import index


class Team(index.Indexed, models.Model):  # type: ignore[django-manager-missing]
    identifier = models.CharField(max_length=255, unique=True)
    name = models.CharField(max_length=255)
    precedence = models.PositiveIntegerField(null=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(default=timezone.now)
    is_active = models.BooleanField(default=True)

    search_fields: ClassVar[list[index.BaseField]] = [
        index.SearchField("name"),
        index.AutocompleteField("name"),
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
