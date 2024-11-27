from functools import cached_property
from typing import ClassVar

from django.db import models
from wagtail.search import index


class Team(index.Indexed, models.Model):
    identifier = models.CharField(max_length=255, unique=True)
    name = models.CharField(max_length=255)
    precedence = models.PositiveIntegerField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
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
    def total_members(self) -> int:
        """Return the total number of users in the team."""
        return self.users.count()

    def get_users_display(self) -> str:
        """Return a comma separated list of users in the team."""
        return ", ".join(user.get_full_name() for user in self.users.all())
