from typing import ClassVar

from django.db import models


class Team(models.Model):
    identifier = models.CharField(max_length=255, unique=True)
    name = models.CharField(max_length=255)
    precedence = models.PositiveIntegerField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering: ClassVar[list[str]] = ["precedence", "name"]

    def __str__(self) -> str:
        return self.name
