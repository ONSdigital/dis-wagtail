from typing import TYPE_CHECKING, ClassVar

from django.conf import settings
from django.db import models
from wagtail.admin.panels import FieldPanel, InlinePanel
from wagtail.fields import RichTextField
from wagtail.search import index

if TYPE_CHECKING:
    from wagtail.admin.panels import Panel


from cms.core.blocks.related import FeaturedItemBlock, RelatedContentBlock
from cms.core.blocks.stream_blocks import CoreStoryBlock
from cms.core.fields import StreamField
from cms.core.models import BasePage


class InformationPage(BasePage):  # type: ignore[django-manager-missing]
    """A generic information page model."""

    template = "templates/pages/information_page.html"

    parent_page_types: ClassVar[list[str]] = ["home.HomePage", "InformationPage", "IndexPage"]

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

    search_fields: ClassVar[list[index.SearchField | index.AutocompleteField]] = [
        *BasePage.search_fields,
        index.SearchField("summary"),
        index.SearchField("content"),
    ]


class IndexPage(BasePage):
    template = "templates/pages/index_page.html"

    parent_page_types: ClassVar[list[str]] = ["home.HomePage", "IndexPage", "InformationPage"]
    subpage_types: ClassVar[list[str]] = ["IndexPage", "InformationPage"]

    description = models.TextField(blank=True)
    featured_items = StreamField([("featured_item", FeaturedItemBlock())], blank=True)
    content = RichTextField(features=settings.RICH_TEXT_BASIC, blank=True)
    related_links = StreamField([("related_link", RelatedContentBlock())], blank=True)

    content_panels: ClassVar[list["Panel"]] = [
        *BasePage.content_panels,
        FieldPanel("description"),
        FieldPanel("featured_items"),
        FieldPanel("content"),
        FieldPanel("related_links"),
    ]

    search_fields: ClassVar[list[index.SearchField | index.AutocompleteField]] = [
        *BasePage.search_fields,
        index.SearchField("description"),
    ]

    def get_formatted_related_links_list(self) -> list[dict[str, str]]:
        """Returns a formatted list of related links for both external and internal pages
        for use with the Design System list component.
        """
        formatted_links = []

        for related_link in self.related_links:
            formatted_links.append(
                {
                    "title": related_link.value.link.get("text"),
                    "url": related_link.value.link.get("url"),
                }
            )

        return formatted_links

    def get_formatted_featured_items(self):
        pass

    def get_context(self, request, *args, **kwargs):
        context = super().get_context(request, *args, **kwargs)

        context["subpages"] = self.get_children().live().public()  # type: ignore[attr-defined]
        context["related_links_list"] = self.get_formatted_related_links_list()

        return context
