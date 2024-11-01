from typing import TYPE_CHECKING, Any, ClassVar

from django.conf import settings
from django.db import models
from django.utils.functional import cached_property
from django.utils.translation import gettext_lazy as _
from modelcluster.fields import ParentalKey
from wagtail.admin.panels import FieldPanel, FieldRowPanel, InlinePanel, MultiFieldPanel
from wagtail.fields import RichTextField
from wagtail.models import Orderable, Page

from cms.core.fields import StreamField
from cms.core.models import BasePage, LinkFieldsMixin

from .blocks import (
    ReleaseCalendarChangesStoryBlock,
    ReleaseCalendarPreReleaseAccessStoryBlock,
    ReleaseCalendarStoryBlock,
)
from .enums import ReleaseStatus
from .forms import ReleaseCalendarPageAdminForm

if TYPE_CHECKING:
    from django.http import HttpRequest


class ReleaseCalendarIndex(BasePage):  # type: ignore[django-manager-missing]
    """The release calendar index page placeholder."""

    template = "templates/pages/release_index.html"

    parent_page_types: ClassVar[list[str]] = ["home.HomePage"]
    subpage_types: ClassVar[list[str]] = ["ReleaseCalendarPage"]
    max_count_per_parent = 1


class ReleasePageRelatedLink(LinkFieldsMixin, Orderable):
    """Related links. e.g. https://www.ons.gov.uk/releases/welshlanguagecensus2021inwales."""

    parent = ParentalKey("ReleaseCalendarPage", related_name="related_links", on_delete=models.CASCADE)


class ReleaseCalendarPage(BasePage):  # type: ignore[django-manager-missing]
    """The calendar release page model."""

    base_form_class = ReleaseCalendarPageAdminForm
    template = "templates/pages/release_calendar/release_calendar_page.html"
    parent_page_types: ClassVar[list[str]] = ["ReleaseCalendarIndex"]
    subpage_types: ClassVar[list[str]] = []

    # Fields
    status = models.CharField(choices=ReleaseStatus.choices, default=ReleaseStatus.PROVISIONAL, max_length=32)
    summary = RichTextField(features=settings.RICH_TEXT_BASIC)

    release_date = models.DateTimeField(
        blank=True, null=True, help_text=_("Required once the release has been confirmed.")
    )
    release_date_text = models.CharField(
        max_length=50, blank=True, help_text=_("Format: 'Month YYYY', or 'Month YYYY to Month YYYY'.")
    )
    next_release_date = models.DateTimeField(blank=True, null=True)
    next_release_text = models.CharField(
        max_length=255, blank=True, help_text=_("Formats needed: 'DD Month YYYY Time' or 'To be confirmed'.")
    )

    notice = RichTextField(
        features=settings.RICH_TEXT_BASIC,
        blank=True,
        help_text=_(
            "Used for data change or cancellation notices. The notice is required when the release is cancelled"
        ),
    )

    content = StreamField(ReleaseCalendarStoryBlock(), blank=True)

    contact_details = models.ForeignKey(
        "core.ContactDetails",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )

    # Fields: about the data
    is_accredited = models.BooleanField(
        _("Accredited Official Statistics"),
        default=False,
        help_text=_(
            "If ticked, will display an information block about the data being accredited official statistics "
            "and include the accredited logo."
        ),
    )
    is_census = models.BooleanField(
        _("Census"),
        default=False,
        help_text=_("If ticked, will display an information block about the data being related to the Census."),
    )

    changes_to_release_date = StreamField(
        ReleaseCalendarChangesStoryBlock(),
        blank=True,
        help_text=_("Required if making changes to confirmed release dates."),
    )
    pre_release_access = StreamField(ReleaseCalendarPreReleaseAccessStoryBlock(), blank=True)

    content_panels: ClassVar[list[FieldPanel]] = [
        MultiFieldPanel(
            [
                *Page.content_panels,
                FieldPanel("status"),
                FieldRowPanel(
                    [
                        FieldPanel("release_date"),
                        FieldPanel("release_date_text", heading=_("Or, release date text")),
                    ],
                    heading="",
                ),
                FieldRowPanel(
                    [
                        FieldPanel("next_release_date"),
                        FieldPanel("next_release_text", heading=_("Or, next release text")),
                    ],
                    heading="",
                ),
                FieldPanel("notice"),
            ],
            heading=_("Metadata"),
            icon="cog",
        ),
        FieldPanel("summary"),
        FieldPanel("content", icon="list-ul"),
        FieldPanel("contact_details", icon="group"),
        MultiFieldPanel(
            [
                FieldPanel("is_accredited"),
                FieldPanel("is_census"),
            ],
            heading=_("About the data"),
            icon="info-circle",
        ),
        FieldPanel("changes_to_release_date", icon="comment"),
        FieldPanel("pre_release_access", icon="key"),
        InlinePanel("related_links", heading=_("Related links"), icon="link"),
    ]

    def get_template(self, request: "HttpRequest", *args: Any, **kwargs: Any) -> str:
        """Select the correct template based on status."""
        if self.status == ReleaseStatus.PROVISIONAL:
            return "templates/pages/release_calendar/release_calendar_page--provisional.html"
        if self.status == ReleaseStatus.CONFIRMED:
            return "templates/pages/release_calendar/release_calendar_page--confirmed.html"
        if self.status == ReleaseStatus.CANCELLED:
            return "templates/pages/release_calendar/release_calendar_page--cancelled.html"
        # assigning to variable to type hint.
        template: str = super().get_template(request, *args, **kwargs)
        return template

    def get_context(self, request: "HttpRequest", *args: Any, **kwargs: Any) -> dict:
        """Additional context for the template."""
        context: dict = super().get_context(request, *args, **kwargs)
        context["related_links"] = self.related_links_for_context
        context["table_of_contents"] = self.table_of_contents
        return context

    @cached_property
    def related_links_for_context(self) -> list[dict[str, str]]:
        """Related links for context."""
        return [
            {
                "text": item.get_link_text(),
                "url": item.get_link_url(),
            }
            for item in self.related_links.select_related("link_page")
        ]

    @cached_property
    def table_of_contents(self) -> list[dict[str, str | object]]:
        """Table of contents formatted to Design System specs."""
        items = [{"url": "#summary", "text": _("Summary")}]

        if self.status == ReleaseStatus.PUBLISHED:
            for block in self.content:  # pylint: disable=not-an-iterable
                items += block.block.to_table_of_contents_items(block.value)

            if self.changes_to_release_date:
                items += [{"url": "#changes-to-release-date", "text": _("Changes to this release date")}]

            if self.contact_details_id:
                items += [{"url": "#contact-details", "text": _("Contact details")}]

        if self.is_accredited or self.is_census:
            items += [{"url": "#about-the-data", "text": _("About the data")}]

        if self.status == ReleaseStatus.PUBLISHED:
            if self.pre_release_access:
                items += [{"url": "#pre-release-access-list", "text": _("Pre-release access list")}]

            if self.related_links_for_context:
                items += [{"url": "#links", "text": _("You might also be interested in")}]

        return items
