from typing import ClassVar

from django.db import models
from modelcluster.fields import ParentalKey
from wagtail.admin.panels import FieldPanel
from wagtail.models import Orderable, Page

__all__ = [
    "PageRelatedPage",
]


class PageRelatedPage(Orderable):
    """Related pages."""

    parent = ParentalKey(Page, related_name="page_related_pages")
    page = models.ForeignKey[Page](
        "wagtailcore.Page",
        on_delete=models.CASCADE,
        related_name="+",
    )

    panels: ClassVar[list[FieldPanel]] = [FieldPanel("page")]
