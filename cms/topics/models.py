from typing import TYPE_CHECKING, ClassVar

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _
from modelcluster.fields import ParentalKey
from wagtail.admin.panels import FieldPanel, InlinePanel, PageChooserPanel
from wagtail.fields import RichTextField
from wagtail.models import Orderable
from wagtail.search import index

from cms.core.fields import StreamField
from cms.core.models import BasePage
from cms.topics.blocks import ExploreMoreStoryBlock

if TYPE_CHECKING:
    from wagtail.admin.panels import Panel


class TopicPageRelatedArticle(Orderable):
    parent = ParentalKey("TopicPage", on_delete=models.CASCADE, related_name="related_articles")
    page = models.ForeignKey(
        "wagtailcore.Page",
        on_delete=models.CASCADE,
        related_name="+",
    )

    panels: ClassVar[list[FieldPanel]] = [PageChooserPanel("page", page_type=["articles.StatisticalArticlePage"])]


class TopicPageRelatedMethodology(Orderable):
    parent = ParentalKey("TopicPage", on_delete=models.CASCADE, related_name="related_methodologies")
    page = models.ForeignKey(
        "wagtailcore.Page",
        on_delete=models.CASCADE,
        related_name="+",
    )

    panels: ClassVar[list[FieldPanel]] = [PageChooserPanel("page", page_type=["methodology.MethodologyPage"])]


class TopicPage(BasePage):  # type: ignore[django-manager-missing]
    """The Topic page model."""

    template = "templates/pages/topic_page.html"
    parent_page_types: ClassVar[list[str]] = ["themes.ThemePage"]
    subpage_types: ClassVar[list[str]] = ["articles.ArticleSeriesPage", "methodology.MethodologyPage"]
    page_description = _("A specific topic page. e.g. 'Public sector finance' or 'Inflation and price indices'.")

    summary = RichTextField(features=settings.RICH_TEXT_BASIC)
    featured_series = models.ForeignKey(
        "articles.ArticleSeriesPage",
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        related_name="featured_on_topic",
    )
    explore_more = StreamField(ExploreMoreStoryBlock(), blank=True)

    content_panels: ClassVar[list["Panel"]] = [
        *BasePage.content_panels,
        FieldPanel("summary"),
        FieldPanel("featured_series", heading=_("Featured")),
        InlinePanel("related_articles", heading=_("Highlighted articles")),
        InlinePanel("related_methodologies", heading=_("Highlighted methods and quality information")),
        FieldPanel("explore_more", heading=_("Explore more")),
    ]

    search_fields: ClassVar[list[index.BaseField]] = [*BasePage.search_fields, index.SearchField("summary")]
