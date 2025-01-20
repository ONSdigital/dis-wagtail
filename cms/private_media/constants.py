from django.db.models import TextChoices
from django.utils.translation import gettext_lazy as _


class Privacy(TextChoices):
    PRIVATE = "private", _("Private")
    PUBLIC = "public", _("Public")
