from typing import TYPE_CHECKING, ClassVar

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _
from wagtail.admin.panels import FieldPanel, FieldRowPanel, MultiFieldPanel, TitleFieldPanel
from wagtail.fields import RichTextField
from wagtail.models import Page

from cms.analysis.blocks import AnalysisStoryBlock
from cms.core.blocks import HeadlineFiguresBlock
from cms.core.fields import StreamField
from cms.core.models import BasePage

if TYPE_CHECKING:
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
