from typing import ClassVar

from django.db import models
from django.db.models import BaseConstraint


class Member(models.Model):
    organisation = models.CharField(max_length=100)
    full_name = models.CharField(max_length=120)
