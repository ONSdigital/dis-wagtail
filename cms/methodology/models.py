from typing import TYPE_CHECKING, Any, ClassVar

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.functional import cached_property
from django.utils.translation import gettext_lazy as _
from wagtail.admin.panels import FieldPanel, FieldRowPanel, InlinePanel, MultiFieldPanel
from wagtail.fields import RichTextField
from wagtail.search import index

from cms.core.blocks.stream_blocks import SectionStoryBlock
from cms.core.fields import StreamField
from cms.core.models import BasePage

if TYPE_CHECKING:
    from django.http import HttpRequest
    from wagtail.admin.panels import Panel


class MethodologyPage(BasePage):  # type: ignore[django-manager-missing]
    parent_page_types: ClassVar[list[str]] = ["topics.TopicPage"]

    template = "templates/pages/methodology_page.html"

    summary = RichTextField(features=settings.RICH_TEXT_BASIC)
    publication_date = models.DateField()
    last_revised_date = models.DateField(blank=True, null=True)

    contact_details = models.ForeignKey(
        "core.ContactDetails",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )

    content = StreamField(SectionStoryBlock())

    show_cite_this_page = models.BooleanField(default=True)

    content_panels: ClassVar[list["Panel"]] = [
        *BasePage.content_panels,
        FieldPanel("summary"),
        MultiFieldPanel(
            [
                FieldRowPanel(
                    [
                        FieldPanel("publication_date",),
                        FieldPanel("last_revised_date"),
                    ]
                ),
                FieldPanel("contact_details"),
                FieldPanel("show_cite_this_page"),
            ],
            heading=_("Metadata"),
            icon="cog",
        ),
        FieldPanel("content", icon="list-ul"),
        InlinePanel("page_related_pages", label="Related publications"),
    ]

    search_fields: ClassVar[list[index.SearchField | index.AutocompleteField]] = [
        *BasePage.search_fields,
        index.SearchField("summary"),
        index.SearchField("content"),
    ]

    def clean(self) -> None:
        """Additional validation on save."""
        super().clean()

        if self.last_revised_date and self.last_revised_date <= self.publication_date:
            raise ValidationError({"last_revised_date": _("The last revised date must be after the published date.")})

    def get_context(self, request: "HttpRequest", *args: Any, **kwargs: Any) -> dict:
        """Additional context for the template."""
        context: dict = super().get_context(request, *args, **kwargs)
        context["table_of_contents"] = self.table_of_contents
        return context

    @cached_property
    def table_of_contents(self) -> list[dict[str, str | object]]:
        """Table of contents formatted to Design System specs."""
        items = []
        for block in self.content:  # pylint: disable=not-an-iterable,useless-suppression
            if hasattr(block.block, "to_table_of_contents_items"):
                items += block.block.to_table_of_contents_items(block.value)
        if self.show_cite_this_page:
            items += [{"url": "#cite-this-page", "text": _("Cite this methodology")}]
        if self.contact_details_id:
            items += [{"url": "#contact-details", "text": _("Contact details")}]
        return items
