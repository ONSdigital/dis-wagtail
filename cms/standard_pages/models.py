from typing import TYPE_CHECKING, Any, ClassVar

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.functional import cached_property
from django.utils.translation import gettext_lazy as _
from wagtail.admin.panels import FieldPanel, InlinePanel, MultiFieldPanel
from wagtail.fields import RichTextField
from wagtail.search import index

from cms.core.blocks.stream_blocks import SectionStoryBlock
from cms.core.fields import StreamField
from cms.core.models import BasePage

if TYPE_CHECKING:
    from django.http import HttpRequest
    from wagtail.admin.panels import Panel


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
    content = StreamField(SectionStoryBlock())

    content_panels: ClassVar[list[FieldPanel]] = [
        *BasePage.content_panels,
        FieldPanel("summary"),
        FieldPanel("last_updated"),
        FieldPanel("content"),
        InlinePanel("page_related_pages", label="Related pages"),
    ]

    search_fields: ClassVar[list[index.SearchField | index.AutocompleteField]] = [
        *BasePage.search_fields,
        index.SearchField("summary"),
        index.SearchField("content"),
    ]
