from typing import TYPE_CHECKING, Any, ClassVar

from django.conf import settings
from django.utils.functional import cached_property
from wagtail.admin.panels import FieldPanel
from wagtail.fields import RichTextField
from wagtail.search import index

from cms.bundles.mixins import BundledPageMixin
from cms.core.analytics_utils import add_table_of_contents_gtm_attributes, format_date_for_gtm
from cms.core.fields import StreamField
from cms.core.forms import PageWithEquationsAdminForm
from cms.core.models import BasePage
from cms.standard_pages.blocks import CoreStoryBlock
from cms.taxonomy.mixins import GenericTaxonomyMixin

if TYPE_CHECKING:
    from django.http import HttpRequest
    from wagtail.admin.panels import Panel


class InformationPage(BundledPageMixin, GenericTaxonomyMixin, BasePage):  # type: ignore[django-manager-missing]
    """A generic information page model."""

    base_form_class = PageWithEquationsAdminForm

    template = "templates/pages/information_page.html"

    parent_page_types: ClassVar[list[str]] = ["IndexPage"]
    # TODO: The below content type needs to be updated
    search_index_content_type: ClassVar[str] = "static_page"

    summary = RichTextField(features=settings.RICH_TEXT_BASIC)
    content = StreamField(CoreStoryBlock())

    _analytics_content_type: ClassVar[str] = "information"

    content_panels: ClassVar[list[Panel]] = [
        *BundledPageMixin.panels,
        *BasePage.content_panels,
        FieldPanel("summary", required_on_save=True),
        FieldPanel("content", required_on_save=True),
    ]

    search_fields: ClassVar[list[index.BaseField]] = [
        *BasePage.search_fields,
        index.SearchField("summary"),
        index.SearchField("content"),
    ]

    @cached_property
    def cached_analytics_values(self) -> dict[str, str | bool]:
        values = super().cached_analytics_values
        if self.last_published_at:
            values["lastUpdatedDate"] = format_date_for_gtm(self.last_published_at)
        return values

    @cached_property
    def table_of_contents(self) -> list[dict[str, str | object]]:
        """Table of contents formatted to Design System specs."""
        items = []
        for block in self.content:  # pylint: disable=not-an-iterable,useless-suppression
            if hasattr(block.block, "to_table_of_contents_items"):
                items += block.block.to_table_of_contents_items(block.value)
        add_table_of_contents_gtm_attributes(items)
        return items

    def get_context(self, request: HttpRequest, *args: Any, **kwargs: Any) -> dict:
        """Additional context for the template."""
        context: dict = super().get_context(request, *args, **kwargs)
        context["table_of_contents"] = self.table_of_contents
        return context


class IndexPage(BundledPageMixin, BasePage):  # type: ignore[django-manager-missing]
    template = "templates/pages/index_page.html"

    page_description = (
        "An index page that serves as a landing hub, listing and signposting users to related pages "
        "within a section, e.g. pages like /help."
    )

    parent_page_types: ClassVar[list[str]] = ["home.HomePage"]
    subpage_types: ClassVar[list[str]] = ["IndexPage", "InformationPage"]
    # TODO: The below content type needs to be updated
    search_index_content_type: ClassVar[str] = "static_landing_page"

    summary = RichTextField(features=settings.RICH_TEXT_BASIC)

    content_panels: ClassVar[list[Panel]] = [
        *BundledPageMixin.panels,
        *BasePage.content_panels,
        FieldPanel("summary", required_on_save=True),
    ]

    search_fields: ClassVar[list[index.SearchField | index.AutocompleteField]] = [
        *BasePage.search_fields,
        index.SearchField("summary"),
    ]

    _analytics_content_type: ClassVar[str] = "index-pages"

    def get_formatted_items(self, request: HttpRequest) -> list[dict[str, str | dict[str, str]]]:
        """Returns a formatted list of Featured items
        that can be either children internal Pages or specified in a RelatedContentBlock
        for use with the Design system Document list component.
        """
        return self._get_formatted_child_pages(request)

    def _get_formatted_child_pages(self, request: HttpRequest) -> list[dict[str, dict[str, str] | Any]]:
        """Format child pages if there are no featured items."""
        formatted_items = []

        qs = self.get_children().specific().defer_streamfields().order_by("title")
        if not getattr(request, "is_preview", False):
            qs = qs.live().public()

        for child_page in qs:
            formatted_items.append(
                {
                    "title": {
                        "text": getattr(child_page, "listing_title", "") or child_page.title,
                        "url": child_page.get_url(request=request),
                    },
                    "description": getattr(child_page, "listing_summary", "") or getattr(child_page, "summary", ""),
                }
            )
        return formatted_items

    def get_context(self, request: HttpRequest, *args: Any, **kwargs: Any) -> dict:
        context: dict = super().get_context(request, *args, **kwargs)

        context["formatted_items"] = self.get_formatted_items(request)

        return context


class CookiesPage(BasePage):  # type: ignore[django-manager-missing]
    """This page is currently intended to be treated as static content, managed by developers, not wagtail users.
    As such, we block all user interactions with it in `cms/standard_pages/wagtail_hooks.py`, and create the pages in
    migrations.

    If the static content in the template changes, we will need to consider manually clearing caches on deployment,
    """

    max_count_per_parent = 1
    template = "templates/pages/cookies.html"

    parent_page_types: ClassVar[list[str]] = ["home.HomePage"]
    _analytics_content_type = "cookies"
