from typing import ClassVar

from django.db import models
from wagtail.admin.panels import FieldPanel

from cms.core.blocks.stream_blocks import CoreStoryBlock
from cms.core.fields import StreamField
from cms.core.models import BasePage


class InformationPage(BasePage):  # type: ignore[django-manager-missing]
    """A Django model for an information page with a template, summary,
    last_updated date, body content, and content panels.
    """

    template = "templates/pages/information_page.html"

    summary = models.TextField(max_length=255, null=True)
    last_updated = models.DateField(blank=True, null=True)
    body = StreamField(CoreStoryBlock())

    content_panels: ClassVar[list[FieldPanel]] = [
        *BasePage.content_panels,
        FieldPanel("summary"),
        FieldPanel("last_updated"),
        FieldPanel("body"),
    ]
