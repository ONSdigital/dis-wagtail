from django.db.models import TextChoices


class Privacy(TextChoices):
    PRIVATE = "private", "Private"
    PUBLIC = "public", "Public"
