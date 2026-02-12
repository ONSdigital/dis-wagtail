from typing import TYPE_CHECKING, Any, ClassVar

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.http import HttpRequest
from django.utils.functional import cached_property
from django.utils.translation import gettext_lazy as _
from modelcluster.fields import ParentalKey
from wagtail.admin.panels import FieldPanel, FieldRowPanel, HelpPanel, InlinePanel, MultiFieldPanel, PageChooserPanel
from wagtail.fields import RichTextField
from wagtail.models import Orderable, Page
from wagtail.search import index

from cms.bundles.mixins import BundledPageMixin
from cms.core.analytics_utils import add_table_of_contents_gtm_attributes, format_date_for_gtm
from cms.core.blocks.stream_blocks import SectionStoryBlock
from cms.core.fields import StreamField
from cms.core.forms import PageWithEquationsAdminForm
from cms.core.models import BasePage
from cms.core.models.mixins import NoTrailingSlashRoutablePageMixin
from cms.core.query import order_by_pk_position
from cms.core.utils import redirect_to_parent_listing
from cms.core.widgets import date_widget
from cms.data_downloads.mixins import DataDownloadMixin
from cms.taxonomy.mixins import GenericTaxonomyMixin

if TYPE_CHECKING:
    import datetime

    from django.http import HttpResponse
    from django_stubs_ext import StrPromise
    from wagtail.admin.panels import Panel
    from wagtail.query import PageQuerySet


class MethodologyIndexPage(BasePage):  # type: ignore[django-manager-missing]
    max_count_per_parent = 1
    parent_page_types: ClassVar[list[str]] = ["topics.TopicPage"]
    page_description = "A place for all methodologies."
    preview_modes: ClassVar[list[str]] = []  # Disabling the preview mode as this redirects away

    content_panels: ClassVar[list[Panel]] = [
        *Page.content_panels,
        HelpPanel(content="This is a container for methodology pages for URL structure purposes."),
    ]
    # disables the "Promote" tab as we control the slug, and the page redirects
    promote_panels: ClassVar[list[Panel]] = []

    def clean(self) -> None:
        self.slug = "methodologies"
        super().clean()

    def minimal_clean(self) -> None:
        # ensure the slug is always set to "methodologies", even for saving drafts, where minimal_clean is used
        self.slug = "methodologies"
        super().minimal_clean()

    def serve(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        # Redirects methodology index page requests to the parent topic's methodologies search URL.
        return redirect_to_parent_listing(
            page=self, request=request, listing_url_method_name="get_methodologies_search_url"
        )


class MethodologyRelatedPage(Orderable):
    """Related pages for Methodology pages."""

    parent = ParentalKey("MethodologyPage", on_delete=models.CASCADE, related_name="related_pages")
    page = models.ForeignKey[Page](
        "wagtailcore.Page",
        on_delete=models.CASCADE,
        related_name="+",
    )

    panels: ClassVar[list[FieldPanel]] = [PageChooserPanel("page", page_type=["articles.StatisticalArticlePage"])]


class MethodologyPage(  # type: ignore[django-manager-missing]
    DataDownloadMixin,
    BundledPageMixin,
    NoTrailingSlashRoutablePageMixin,
    GenericTaxonomyMixin,
    BasePage,
):
    base_form_class = PageWithEquationsAdminForm
    parent_page_types: ClassVar[list[str]] = ["MethodologyIndexPage"]
    search_index_content_type: ClassVar[str] = "static_methodology"
    template = "templates/pages/methodology_page.html"
    label = _("Methodology")  # type: ignore[assignment]

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

    content_panels: ClassVar[list[Panel]] = [
        *BundledPageMixin.panels,
        *BasePage.content_panels,
        FieldPanel("summary", required_on_save=True),
        MultiFieldPanel(
            [
                FieldRowPanel(
                    [
                        FieldPanel("publication_date", date_widget),
                        FieldPanel("last_revised_date", date_widget),
                    ]
                ),
                "contact_details",
                "show_cite_this_page",
            ],
            heading="Metadata",
            icon="cog",
        ),
        FieldPanel("content", icon="list-ul", required_on_save=True),
        InlinePanel("related_pages", label="Related publications"),
    ]

    search_fields: ClassVar[list[index.BaseField]] = [
        *BasePage.search_fields,
        index.SearchField("summary"),
        index.SearchField("content"),
    ]

    _analytics_content_type: ClassVar[str] = "methodologies"

    def clean(self) -> None:
        """Additional validation on save."""
        super().clean()

        if self.last_revised_date and self.last_revised_date <= self.publication_date:
            raise ValidationError({"last_revised_date": "The last revised date must be after the published date."})

    def get_context(self, request: HttpRequest, *args: Any, **kwargs: Any) -> dict:
        """Additional context for the template."""
        context: dict = super().get_context(request, *args, **kwargs)
        context["table_of_contents"] = self.table_of_contents
        context["related_publications"] = self.get_formatted_related_publications_list(request=request)
        return context

    @property
    def release_date(self) -> datetime.date:
        return self.publication_date

    @cached_property
    def related_publications(self) -> PageQuerySet:
        """Return a `PageQuerySet` of the StatisticalArticlePage page model via the
        `MethodologyRelatedPage` through model, which is suitable for display.
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

    def get_formatted_related_publications_list(
        self, request: HttpRequest | None = None
    ) -> dict[str, str | StrPromise | list[dict[str, str]]]:
        """Returns a formatted list of related internal pages for use with the Design System list component."""
        items = [
            {
                "title": getattr(page, "display_title", page.title),
                "url": page.get_url(request=request),
            }
            for page in self.related_publications
        ]

        return {"title": _("Related publications"), "itemsList": items} if items else {}

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
        add_table_of_contents_gtm_attributes(items)
        return items

    @cached_property
    def cached_analytics_values(self) -> dict[str, str | bool]:
        values = super().cached_analytics_values
        if self.last_revised_date:
            values["lastUpdatedDate"] = format_date_for_gtm(self.last_revised_date)
        return values
