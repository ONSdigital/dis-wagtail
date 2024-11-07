from typing import ClassVar

from django.db import models
from wagtail.admin.panels import FieldPanel

from cms.core.blocks.stream_blocks import CoreStoryBlock
from cms.core.fields import StreamField
from cms.core.models import BasePage


class InformationPage(BasePage):  # type: ignore[django-manager-missing]
    """A Django model representing an information page.

    Attributes:
        template (str): The path to the template used to render this page.
        summary (TextField): A brief summary of the page content, with a maximum length of 255 characters.
        last_updated (DateField): The date when the page was last updated.
        body (StreamField): The main content of the page, using a custom StreamField block.
        content_panels (list[FieldPanel]): The list of content panels for the Wagtail admin interface.
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
