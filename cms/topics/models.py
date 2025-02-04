from typing import TYPE_CHECKING, Any, ClassVar

from django.conf import settings
from django.db import models
from django.db.models import OuterRef, QuerySet, Subquery
from django.utils.functional import cached_property
from django.utils.translation import gettext_lazy as _
from modelcluster.fields import ParentalKey
from wagtail.admin.panels import FieldPanel, InlinePanel, PageChooserPanel
from wagtail.fields import RichTextField
from wagtail.models import Orderable, Page
from wagtail.search import index

from cms.articles.models import ArticleSeriesPage, StatisticalArticlePage
from cms.core.fields import StreamField
from cms.core.models import BasePage
from cms.methodology.models import MethodologyPage
from cms.topics.blocks import ExploreMoreStoryBlock

if TYPE_CHECKING:
    from django.http import HttpRequest
    from django.utils.functional import Promise
    from wagtail.admin.panels import Panel


class TopicPageRelatedArticle(Orderable):
    parent = ParentalKey("TopicPage", on_delete=models.CASCADE, related_name="related_articles")
    page = models.ForeignKey[Page](
        "wagtailcore.Page",
        on_delete=models.CASCADE,
        related_name="+",
    )

    panels: ClassVar[list[FieldPanel]] = [PageChooserPanel("page", page_type=["articles.StatisticalArticlePage"])]


class TopicPageRelatedMethodology(Orderable):
    parent = ParentalKey("TopicPage", on_delete=models.CASCADE, related_name="related_methodologies")
    page = models.ForeignKey[Page](
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

    def get_context(self, request: "HttpRequest", *args: Any, **kwargs: Any) -> dict:
        """Additional context for the template."""
        context: dict = super().get_context(request, *args, **kwargs)
        context["table_of_contents"] = self.table_of_contents
        context["featured_item"] = self.latest_article_in_featured_series
        return context

    @property
    def label(self) -> "Promise":
        return _("Topic")

    @cached_property
    def latest_article_in_featured_series(self) -> StatisticalArticlePage | None:
        """Returns the latest article in the featured series."""
        article: StatisticalArticlePage | None = StatisticalArticlePage.objects.none()
        if self.featured_series:
            article = (
                StatisticalArticlePage.objects.child_of(self.featured_series)
                .live()
                .public()
                .order_by("-release_date")
                .first()
            )
        return article

    @cached_property
    def processed_articles(self) -> QuerySet[ArticleSeriesPage]:
        """Returns the latest articles in the series relevant for this topic."""
        newest_qs = (
            StatisticalArticlePage.objects.live()
            .public()
            .filter(path__startswith=OuterRef("path"), depth__gte=OuterRef("depth"))
        )
        newest_qs = newest_qs.order_by("-release_date")
        latest_by_series = (
            ArticleSeriesPage.objects.child_of(self)
            .annotate(latest_child_page=Subquery(newest_qs.values("pk")[:1]))
            .values_list("latest_child_page", flat=True)
        )

        return StatisticalArticlePage.objects.filter(pk__in=latest_by_series).order_by("-release_date")[:3]

    @cached_property
    def processed_methodologies(self) -> QuerySet[MethodologyPage]:
        pages: QuerySet[MethodologyPage] = MethodologyPage.objects.child_of(self).live().public()[:3]
        return pages

    @cached_property
    def table_of_contents(self) -> list[dict[str, str | object]]:
        """Table of contents formatted to Design System specs."""
        items = []
        if self.latest_article_in_featured_series:
            items += [{"url": "#featured", "text": _("Featured")}]
        if self.processed_articles:  # pylint: disable=not-an-iterable,useless-suppression
            items += [{"url": "#related-articles", "text": _("Related articles")}]
        if self.processed_methodologies:
            items += [{"url": "#related-methods", "text": _("Methods and quality information")}]
        if self.explore_more:
            items += [{"url": "#explore-more", "text": _("Explore more")}]
        return items
