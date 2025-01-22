from typing import ClassVar

from django.db import models
from wagtail.admin.panels import FieldPanel, InlinePanel
from wagtail.search import index

from cms.core.blocks.stream_blocks import CoreStoryBlock
from cms.core.fields import StreamField
from cms.core.models import BasePage


class InformationPage(BasePage):  # type: ignore[django-manager-missing]
    """A generic information page model."""

    template = "templates/pages/information_page.html"

    parent_page_types: ClassVar[list[str]] = [
        # Ensures that the information page can only be created under the home page
        "home.HomePage",
        # Ensures that the information page can be created under another information page
        "standard_pages.InformationPage",
    ]

    summary = models.TextField(max_length=255)
    last_updated = models.DateField(blank=True, null=True)
    content = StreamField(CoreStoryBlock())

    content_panels: ClassVar[list[FieldPanel]] = [
        *BasePage.content_panels,
        FieldPanel("summary"),
        FieldPanel("last_updated"),
        FieldPanel("content"),
        InlinePanel("page_related_pages", label="Related pages"),
    ]

    search_fields: ClassVar[list[index.BaseField]] = [
        *BasePage.search_fields,
        index.SearchField("summary"),
        index.SearchField("content"),
    ]
