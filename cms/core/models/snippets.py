from typing import Any, ClassVar

from django.db import models
from django.utils.translation import gettext_lazy as _
from wagtail.admin.panels import FieldPanel
from wagtail.search import index


class ContactDetails(index.Indexed, models.Model):
    """A model for contact details.

    Note that this is registered as a snippet in core.wagtail_hooks to allow customising the icon.
    """

    name = models.CharField(max_length=255, unique=True)
    email = models.EmailField()
    phone = models.CharField(max_length=255, blank=True)

    panels: ClassVar[list[FieldPanel]] = [
        FieldPanel("name"),
        FieldPanel("email"),
        FieldPanel("phone"),
    ]

    search_fields: ClassVar[list[index.SearchField | index.AutocompleteField]] = [
        *index.Indexed.search_fields,
        index.SearchField("name"),
        index.AutocompleteField("name"),
        index.SearchField("email"),
        index.SearchField("phone"),
    ]

    class Meta:
        verbose_name = _("contact details")
        verbose_name_plural = _("contact details")

    def save(self, *args: Any, **kwargs: Any) -> None:
        if self.name:
            self.name = self.name.strip()
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return str(self.name)
