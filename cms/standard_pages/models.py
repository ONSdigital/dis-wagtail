from typing import TYPE_CHECKING, Any, ClassVar

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _
from wagtail.admin.panels import FieldPanel, InlinePanel
from wagtail.fields import RichTextField
from wagtail.search import index

from cms.core.blocks.related import RelatedContentBlock
from cms.core.blocks.stream_blocks import CoreStoryBlock
from cms.core.fields import StreamField
from cms.core.models import BasePage

if TYPE_CHECKING:
    from django.http import HttpRequest
    from wagtail.admin.panels import Panel


class InformationPage(BasePage):  # type: ignore[django-manager-missing]
    """A generic information page model."""

    template = "templates/pages/information_page.html"

    parent_page_types: ClassVar[list[str]] = ["home.HomePage", "InformationPage", "IndexPage"]

    summary = RichTextField(features=settings.RICH_TEXT_BASIC)
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


class IndexPage(BasePage):  # type: ignore[django-manager-missing]
    template = "templates/pages/index_page.html"

    parent_page_types: ClassVar[list[str]] = ["home.HomePage", "IndexPage"]
    subpage_types: ClassVar[list[str]] = ["IndexPage", "InformationPage"]

    summary = RichTextField(features=settings.RICH_TEXT_BASIC)
    featured_items = StreamField(
        [("featured_item", RelatedContentBlock())],
        help_text=_("Leave blank to automatically populate with child pages. Only published pages will be displayed."),
        blank=True,
    )

    content = RichTextField(features=settings.RICH_TEXT_BASIC, blank=True)
    related_links = StreamField([("related_link", RelatedContentBlock())], blank=True)

    content_panels: ClassVar[list["Panel"]] = [
        *BasePage.content_panels,
        FieldPanel("summary"),
        FieldPanel("featured_items"),
        FieldPanel("content"),
        FieldPanel("related_links"),
    ]

    search_fields: ClassVar[list[index.SearchField | index.AutocompleteField]] = [
        *BasePage.search_fields,
        index.SearchField("summary"),
        index.SearchField("content"),
    ]

    def get_formatted_items(self, request: "HttpRequest") -> list[dict[str, str | dict[str, str]]]:
        """Returns a formatted list of Featured items
        that can be either children internal Pages or specified in a RelatedContentBlock
        for use with the Design system Document list component.
        """

        def get_featured_item_dict(title: str, url: str, description: str) -> dict[str, str | dict[str, str]]:
            """Helper to create the featured item dictionary."""
            return {
                "featured": "true",
                "title": {"text": title, "url": url},
                "description": description,
            }

        formatted_items = []

        for featured_item in self.featured_items:  # pylint: disable=not-an-iterable
            if featured_item.value.link is None:
                continue

            formatted_items.append(
                get_featured_item_dict(
                    title=featured_item.value.link["text"],
                    url=featured_item.value.link["url"],
                    description=featured_item.value["description"],
                )
            )

        if not formatted_items:
            for child_page in self.get_children().live().public().specific().defer_streamfields():
                formatted_items.append(
                    get_featured_item_dict(
                        title=getattr(child_page, "listing_title", "") or child_page.title,
                        url=child_page.get_url(request=request),
                        description=getattr(child_page, "listing_summary", "") or getattr(child_page, "summary", ""),
                    )
                )

        return formatted_items

    def get_formatted_related_links_list(self) -> list[dict[str, str]]:
        """Returns a formatted list of related links for both external and internal pages
        for use with the Design System list component.
        """
        formatted_links = [
            {
                "title": related_link.value.link.get("text"),
                "url": related_link.value.link.get("url"),
            }
            for related_link in self.related_links  # pylint: disable=not-an-iterable
        ]

        return formatted_links

    def get_context(self, request: "HttpRequest", *args: Any, **kwargs: Any) -> dict:
        context: dict = super().get_context(request, *args, **kwargs)

        context["formatted_items"] = self.get_formatted_items(request)
        context["related_links_list"] = self.get_formatted_related_links_list()

        return context
