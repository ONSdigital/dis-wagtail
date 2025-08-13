from typing import ClassVar

from django.db import models


class Widget(models.Model):
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=40, null=True, blank=True)

    class Meta:
        constraints: ClassVar[list[models.BaseConstraint]] = [
            models.UniqueConstraint(
                fields=["code"],
                name="u_demo_widget_code",  # fixed name to provoke duplicate error
            )
        ]
