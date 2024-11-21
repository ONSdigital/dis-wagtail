from typing import ClassVar

from django.contrib.auth import get_user_model
from django.db import models


class Team(models.Model):
    identifier = models.CharField(max_length=255, unique=True)
    name = models.CharField(max_length=255)
    precedence = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    members = models.ManyToManyField(get_user_model(), related_name="teams", blank=True)  # type: ignore[var-annotated]

    class Meta:
        ordering: ClassVar[list[str]] = ["precedence", "name"]

    def __str__(self) -> str:
        return self.name
