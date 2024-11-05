from functools import cached_property
from typing import TYPE_CHECKING, Any, ClassVar

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _
from wagtail.admin.panels import FieldPanel, FieldRowPanel, MultiFieldPanel, TitleFieldPanel
from wagtail.fields import RichTextField
from wagtail.models import Page
from wagtail.search import index

from cms.analysis.blocks import AnalysisStoryBlock
from cms.core.blocks import HeadlineFiguresBlock
from cms.core.fields import StreamField
from cms.core.models import BasePage

if TYPE_CHECKING:
    from django.http import HttpRequest
    from wagtail.admin.panels import Panel


class AnalysisSeries(Page):  # type: ignore[django-manager-missing]
    """The analysis series model."""

    parent_page_types: ClassVar[list[str]] = ["topics.TopicPage"]
    subpage_types: ClassVar[list[str]] = ["AnalysisPage"]
    preview_modes: ClassVar[list[str]] = []  # Disabling the preview mode due to it being a container page.
    page_description = "A container for Analysis series"


class AnalysisPage(BasePage):  # type: ignore[django-manager-missing]
    """The analysis page model."""

    parent_page_types: ClassVar[list[str]] = ["AnalysisSeries"]
    subpage_types: ClassVar[list[str]] = []
    template = "templates/pages/analysis_page.html"

    # Fields
    news_headline = models.CharField(max_length=255, blank=True)
    summary = RichTextField(features=settings.RICH_TEXT_BASIC)

    main_points = RichTextField(features=settings.RICH_TEXT_BASIC, help_text=_("Used when featured on a topic page."))

    # Fields: dates
    release_date = models.DateField()
    next_release_date = models.DateField(blank=True, null=True)

    contact_details = models.ForeignKey(
        "core.ContactDetails",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )

    # Fields: accredited/census. A bit of "about the data".
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

    # Fields: content
    headline_figures = StreamField([("figures", HeadlineFiguresBlock())], blank=True, max_num=1)
    content = StreamField(AnalysisStoryBlock())

    show_cite_this_page = models.BooleanField(default=True)

    content_panels: ClassVar[list["Panel"]] = [
        MultiFieldPanel(
            [
                TitleFieldPanel("title", help_text=_("Also known as the release edition. e.g. 'November 2024'.")),
                FieldPanel(
                    "news_headline",
                    help_text=(
                        "Use this as a news headline. When populated, replaces the title displayed on the page. "
                        "Note: the page slug is powered by the title field. "
                        "You can change the slug in the 'Promote' tab."
                    ),
                    icon="news",
                ),
            ],
            heading="Title",
        ),
        FieldPanel("summary"),
        MultiFieldPanel(
            [
                FieldPanel("release_date", icon="calendar-date"),
                FieldPanel(
                    "next_release_date",
                    help_text=_("If no next date is chosen, 'To be announced' will be displayed."),
                ),
                FieldRowPanel(
                    [FieldPanel("is_accredited"), FieldPanel("is_census")],
                    heading=_("About the data"),
                ),
                FieldPanel("contact_details"),
                FieldPanel("show_cite_this_page"),
                FieldPanel("main_points"),
            ],
            heading=_("Metadata"),
            icon="cog",
        ),
        FieldPanel("headline_figures", icon="data-analysis"),
        FieldPanel("content", icon="list-ul"),
    ]

    search_fields: ClassVar[list[index.SearchField | index.AutocompleteField]] = [
        *BasePage.search_fields,
        index.SearchField("summary"),
        index.SearchField("headline_figures"),
        index.SearchField("content"),
        index.SearchField("get_admin_display_title", boost=2),
        index.AutocompleteField("get_admin_display_title"),
        index.SearchField("news_headline"),
        index.AutocompleteField("news_headline"),
    ]

    def get_context(self, request: "HttpRequest", *args: Any, **kwargs: Any) -> dict:
        """Additional context for the template."""
        context: dict = super().get_context(request, *args, **kwargs)
        context["table_of_contents"] = self.table_of_contents
        return context

    def get_admin_display_title(self) -> str:
        """Changes the admin display title to include the parent title."""
        return f"{self.get_parent().title}: {self.draft_title or self.title}"

    @property
    def display_title(self) -> str:
        """Returns the page display title. If the news headline is set, it takes precedence over the series+title."""
        return self.news_headline.strip() or self.get_admin_display_title()

    @cached_property
    def table_of_contents(self) -> list[dict[str, str | object]]:
        """Table of contents formatted to Design System specs."""
        items = []
        for block in self.content:  # pylint: disable=not-an-iterable,useless-suppression
            if hasattr(block.block, "to_table_of_contents_items"):
                items += block.block.to_table_of_contents_items(block.value)
        if self.show_cite_this_page:
            items += [{"url": "#cite-this-page", "text": _("Cite this analysis")}]
        if self.contact_details_id:
            items += [{"url": "#contact-details", "text": _("Contact details")}]
        return items

    @cached_property
    def has_equations(self) -> bool:
        """Checks if there are any equation blocks."""
        return any(
            block.value["content"].first_block_by_name("equation") is not None
            for block in self.content  # pylint: disable=not-an-iterable
        )

    @cached_property
    def has_ons_embed(self) -> bool:
        """Checks if there are any ONS embed blocks."""
        return any(
            block.value["content"].first_block_by_name("ons_embed") is not None
            for block in self.content  # pylint: disable=not-an-iterable
        )
