from collections.abc import Sequence
from typing import TYPE_CHECKING, Any, ClassVar, Optional, cast

from django.conf import settings
from django.db import models
from django.utils.functional import cached_property
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _
from wagtail.admin.panels import FieldPanel, FieldRowPanel, MultiFieldPanel
from wagtail.fields import RichTextField
from wagtail.models import Page
from wagtail.search import index

from cms.bundles.mixins import BundledPageMixin
from cms.core.analytics_utils import add_table_of_contents_gtm_attributes, format_date_for_gtm
from cms.core.custom_date_format import ons_date_format, ons_default_datetime
from cms.core.fields import StreamField
from cms.core.models import BasePage
from cms.core.widgets import ONSAdminDateTimeInput
from cms.datasets.blocks import DatasetStoryBlock
from cms.datasets.utils import format_datasets_as_document_list

from .blocks import (
    ReleaseCalendarChangesStoryBlock,
    ReleaseCalendarPreReleaseAccessStoryBlock,
    ReleaseCalendarRelatedLinksStoryBlock,
    ReleaseCalendarStoryBlock,
)
from .enums import NON_PROVISIONAL_STATUSES, ReleaseStatus
from .forms import ReleaseCalendarPageAdminForm
from .locks import ReleasePageInBundleReadyToBePublishedLock
from .panels import ChangesToReleaseDateFieldPanel, ReleaseCalendarBundleNotePanel

if TYPE_CHECKING:
    from django.http import HttpRequest
    from django.template.response import TemplateResponse
    from wagtail.locks import BaseLock

    from cms.bundles.models import Bundle


class ReleaseCalendarIndex(BasePage):  # type: ignore[django-manager-missing]
    """The release calendar index page placeholder."""

    template = "templates/pages/release_index.html"

    parent_page_types: ClassVar[list[str]] = ["home.HomePage"]
    subpage_types: ClassVar[list[str]] = ["ReleaseCalendarPage"]
    max_count_per_parent = 1


class ReleaseCalendarPage(BundledPageMixin, BasePage):  # type: ignore[django-manager-missing]
    """The calendar release page model."""

    base_form_class = ReleaseCalendarPageAdminForm
    template = "templates/pages/release_calendar/release_calendar_page.html"
    parent_page_types: ClassVar[list[str]] = ["ReleaseCalendarIndex"]
    subpage_types: ClassVar[list[str]] = []
    search_index_content_type: ClassVar[str] = "release"

    # Fields
    status = models.CharField(choices=ReleaseStatus.choices, default=ReleaseStatus.PROVISIONAL, max_length=32)
    summary = RichTextField(features=settings.RICH_TEXT_BASIC)

    release_date = models.DateTimeField(blank=False, null=False, default=ons_default_datetime)
    release_date_text = models.CharField(
        max_length=50,
        blank=True,
        help_text="Override release date for provisional entries. Format: 'Month YYYY', or 'Month YYYY to Month YYYY'.",
    )
    next_release_date = models.DateTimeField(blank=True, null=True)
    next_release_date_text = models.CharField(
        max_length=255,
        blank=True,
        help_text="Format: 'DD Month YYYY Time' or 'To be confirmed'.",
    )

    notice = RichTextField(
        features=settings.RICH_TEXT_BASIC,
        verbose_name="Cancellation notice",
        blank=True,
        help_text=(
            "Used for data change or cancellation notices. The notice is required when the release is cancelled"
        ),
    )

    content = StreamField(
        ReleaseCalendarStoryBlock(),
        blank=True,
        help_text=("This is usually through the bundle release process, but can also be manually set."),
    )
    datasets = StreamField(DatasetStoryBlock(), blank=True, default=list)

    contact_details = models.ForeignKey(
        "core.ContactDetails",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )

    # Fields: about the data
    is_accredited = models.BooleanField(
        "Accredited Official Statistics",
        default=False,
        help_text=(
            "If ticked, will display an information block about the data being accredited official statistics "
            "and include the accredited logo."
        ),
    )
    is_census = models.BooleanField(
        "Census",
        default=False,
        help_text="If ticked, will display an information block about the data being related to the Census.",
    )

    changes_to_release_date = StreamField(
        ReleaseCalendarChangesStoryBlock(),
        blank=True,
        help_text="Required if making changes to confirmed release dates.",
    )
    pre_release_access = StreamField(ReleaseCalendarPreReleaseAccessStoryBlock(), blank=True)
    related_links = StreamField(ReleaseCalendarRelatedLinksStoryBlock(), blank=True)

    content_panels: ClassVar[list[FieldPanel]] = [
        *BundledPageMixin.panels,
        MultiFieldPanel(
            [
                *Page.content_panels,
                "status",
                ReleaseCalendarBundleNotePanel(heading="Note", classname="bundle-note"),
                FieldRowPanel(
                    [
                        FieldPanel(
                            "release_date",
                            widget=ONSAdminDateTimeInput(),
                            required_on_save=True,
                        ),
                        FieldPanel("release_date_text", heading="Or, release date text"),
                    ],
                    heading="",
                ),
                FieldRowPanel(
                    [
                        FieldPanel("next_release_date", widget=ONSAdminDateTimeInput()),
                        FieldPanel(
                            "next_release_date_text",
                            heading="Or, next release date text",
                        ),
                    ],
                    heading="",
                ),
                "notice",
            ],
            heading="Metadata",
            icon="cog",
        ),
        FieldPanel("summary", required_on_save=True),
        FieldPanel("content", icon="list-ul", required_on_save=True),
        FieldPanel(
            "datasets",
            help_text="Select the datasets that this release relates to.",
            icon="doc-full",
        ),
        FieldPanel("contact_details", icon="group"),
        MultiFieldPanel(
            [
                "is_accredited",
                "is_census",
            ],
            heading="About the data",
            icon="info-circle",
        ),
        ChangesToReleaseDateFieldPanel("changes_to_release_date", icon="comment"),
        FieldPanel("pre_release_access", icon="key"),
        FieldPanel("related_links", icon="link"),
    ]

    search_fields: ClassVar[list[index.BaseField]] = [
        *BasePage.search_fields,
        index.FilterField("status"),
        index.FilterField("release_date"),
    ]

    _analytics_content_type: ClassVar[str] = "release-calendars"  # TODO agree in spec

    def get_template(self, request: "HttpRequest", *args: Any, **kwargs: Any) -> str:
        """Select the correct template based on status."""
        template_by_status = {
            ReleaseStatus.PROVISIONAL.value: "provisional.html",
            ReleaseStatus.CONFIRMED.value: "confirmed.html",
            ReleaseStatus.CANCELLED.value: "cancelled.html",
        }
        if template_for_status := template_by_status.get(self.status):
            return f"templates/pages/release_calendar/release_calendar_page--{template_for_status}"

        # assigning to variable to type hint.
        template: str = super().get_template(request, *args, **kwargs)
        return template

    def get_context(self, request: "HttpRequest", *args: Any, **kwargs: Any) -> dict:
        """Additional context for the template."""
        context: dict = super().get_context(request, *args, **kwargs)
        context["table_of_contents"] = self.table_of_contents
        return context

    @property
    def release_date_value(self) -> str:
        if self.release_date_text and self.status == ReleaseStatus.PROVISIONAL:
            return self.release_date_text
        return ons_date_format(self.release_date, "DATETIME_FORMAT")

    @property
    def next_release_date_value(self) -> str | None:
        if self.next_release_date:
            return ons_date_format(self.next_release_date, "DATETIME_FORMAT")
        if self.next_release_date_text:
            return self.next_release_date_text
        return None

    @cached_property
    def dataset_document_list(self) -> list[dict[str, Any]]:
        return format_datasets_as_document_list(self.datasets)

    @cached_property
    def table_of_contents(self) -> list[dict[str, Any]]:
        """Table of contents formatted to Design System specs."""
        items = [{"url": "#summary", "text": _("Summary")}]

        if self.status == ReleaseStatus.PUBLISHED:
            for block in self.content:
                items += block.block.to_table_of_contents_items(block.value)

            if self.dataset_document_list:
                items += [{"url": "#datasets", "text": _("Data")}]

        if self.status in NON_PROVISIONAL_STATUSES and self.changes_to_release_date:
            items += [
                {
                    "url": "#changes-to-release-date",
                    "text": _("Changes to this release date"),
                }
            ]

        if self.status == ReleaseStatus.PUBLISHED and self.contact_details_id:
            text = _("Contact details")
            items += [{"url": f"#{slugify(text)}", "text": text}]

        if self.is_accredited or self.is_census:
            text = _("About the data")
            items += [{"url": f"#{slugify(text)}", "text": text}]

        if self.status == ReleaseStatus.PUBLISHED:
            if self.pre_release_access:
                text = _("Pre-release access list")
                items += [{"url": f"#{slugify(text)}", "text": text}]

            if self.related_links:
                items += [{"url": "#links", "text": _("You might also be interested in")}]
        add_table_of_contents_gtm_attributes(items)
        return items

    @cached_property
    def active_bundle(self) -> Optional["Bundle"]:
        if not self.pk:
            return None
        bundle: Bundle | None = self.bundles.active().first()
        return bundle

    @property
    def live_status(self) -> ReleaseStatus | None:
        if not self.pk:
            return None
        # We just want one field, so we don't use live_revision
        # to avoid loading the whole revision object.
        live_page = ReleaseCalendarPage.objects.filter(pk=self.pk).live().only("status").first()
        return live_page.status if live_page else None

    @property
    def live_notice(self) -> str | None:
        if not self.pk:
            return None
        live_page = ReleaseCalendarPage.objects.filter(pk=self.pk).live().only("notice").first()
        return live_page.notice if live_page else None

    @property
    def preview_modes(self) -> Sequence[tuple[str, str]]:
        return ReleaseStatus.choices

    def get_preview_template(self, request: None, mode_name: str) -> "TemplateResponse":
        templates = {
            "PROVISIONAL": "templates/pages/release_calendar/release_calendar_page--provisional.html",
            "CONFIRMED": "templates/pages/release_calendar/release_calendar_page--confirmed.html",
            "CANCELLED": "templates/pages/release_calendar/release_calendar_page--cancelled.html",
            "PUBLISHED": "templates/pages/release_calendar/release_calendar_page.html",
        }

        return cast("TemplateResponse", templates.get(mode_name, templates["PROVISIONAL"]))

    def get_lock(self) -> Optional["BaseLock"]:
        if self.active_bundle and self.active_bundle.is_ready_to_be_published:
            return ReleasePageInBundleReadyToBePublishedLock(self)

        return super().get_lock()

    @cached_property
    def cached_analytics_values(self) -> dict[str, str | bool]:
        values = super().cached_analytics_values
        if self.next_release_date:
            values["nextReleaseDate"] = format_date_for_gtm(self.next_release_date)
        return values
