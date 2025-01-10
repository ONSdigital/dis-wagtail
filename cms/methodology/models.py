from typing import TYPE_CHECKING, Any, ClassVar

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.http import HttpRequest
from django.utils.functional import cached_property
from django.utils.translation import gettext_lazy as _
from modelcluster.fields import ParentalKey
from wagtail.admin.panels import FieldPanel, FieldRowPanel, InlinePanel, MultiFieldPanel, PageChooserPanel
from wagtail.fields import RichTextField
from wagtail.models import Orderable, Page
from wagtail.search import index

from cms.core.blocks.stream_blocks import SectionStoryBlock
from cms.core.fields import StreamField
from cms.core.models import BasePage
from cms.core.query import order_by_pk_position

if TYPE_CHECKING:
    from wagtail.admin.panels import Panel
    from wagtail.query import PageQuerySet


class MethodologyRelatedPage(Orderable):
    """Related pages for Methodology pages."""

    parent = ParentalKey("MethodologyPage", on_delete=models.CASCADE, related_name="related_pages")
    page = models.ForeignKey[Page](
        "wagtailcore.Page",
        on_delete=models.CASCADE,
        related_name="+",
    )

    panels: ClassVar[list[FieldPanel]] = [PageChooserPanel("page", page_type=["articles.StatisticalArticlePage"])]


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
                        FieldPanel(
                            "publication_date",
                        ),
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
        InlinePanel("related_pages", label="Related publications"),
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

    def get_context(self, request: HttpRequest, *args: Any, **kwargs: Any) -> dict:
        """Additional context for the template."""
        context: dict = super().get_context(request, *args, **kwargs)
        context["table_of_contents"] = self.table_of_contents
        context["related_publications"] = self.get_formatted_related_publications_list(request=request)
        return context

    @cached_property
    def related_publications(self) -> "PageQuerySet":
        """Return a `PageQuerySet` of items related to this page via the
        `PageRelatedPage` through model, and are suitable for display.
        The result is ordered to match that specified by editors using
        the 'page_related_pages' `InlinePanel`.
        """
        # NOTE: avoiding values_list() here for compatibility with preview
        # See: https://github.com/wagtail/django-modelcluster/issues/30
        ordered_page_pks = tuple(item.page_id for item in self.related_pages.all().only("page"))
        return order_by_pk_position(
            Page.objects.live().public().specific(),
            pks=ordered_page_pks,
            exclude_non_matches=True,
        )

    def get_formatted_related_publications_list(self, request: HttpRequest | None = None) -> list[dict[str, str]]:
        """Returns a formatted list of related publications for use with the Design System list component."""
        items = []
        for page in self.related_publications:
            items.append(
                {
                    "title": getattr(page, "display_title", page.title),
                    "url": page.get_url(request=request),
                }
            )
        return items

    @cached_property
    def table_of_contents(self) -> list[dict[str, str | object]]:
        """Table of contents formatted to Design System specs."""
        items = []
        for block in self.content:  # pylint: disable=not-an-iterable,useless-suppression
            if hasattr(block.block, "to_table_of_contents_items"):
                items += block.block.to_table_of_contents_items(block.value)
        if self.related_publications:
            items += [{"url": "#related-publications", "text": _("Related publications")}]
        if self.show_cite_this_page:
            items += [{"url": "#cite-this-page", "text": _("Cite this methodology")}]
        if self.contact_details_id:
            items += [{"url": "#contact-details", "text": _("Contact details")}]
        return items
