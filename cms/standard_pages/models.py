from typing import ClassVar

from django.db import models
from wagtail.admin.panels import FieldPanel

# from cms.core.models import BasePage
from wagtail.fields import StreamField
from wagtail.models import Page

from cms.core.blocks.stream_blocks import CoreStoryBlock


class InformationPage(Page):
    template = "templates/pages/information_page.html"

    description = models.TextField(max_length=255, null=True)
    last_updated = models.DateField(blank=True, null=True)
    body = StreamField(CoreStoryBlock(), use_json_field=True)

    # content_panels = Page.content_panels + [
    #     FieldPanel("description"),
    #     FieldPanel("last_updated"),
    #     FieldPanel("body"),
    # ]

    content_panels: ClassVar[list[FieldPanel]] = [
        *Page.content_panels,
        FieldPanel("description"),
        FieldPanel("last_updated"),
        FieldPanel("body"),
    ]
