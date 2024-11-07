from typing import ClassVar

from django.db import models
from wagtail.admin.panels import FieldPanel

from cms.core.blocks.stream_blocks import CoreStoryBlock
from cms.core.fields import StreamField
from cms.core.models import BasePage


class InformationPage(BasePage):
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
