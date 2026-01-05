from abc import ABC, abstractmethod
from collections.abc import Iterable
from typing import TYPE_CHECKING

from django.db.models import OuterRef, Q, Subquery
from django.db.models.functions import Coalesce

from cms.articles.models import ArticleSeriesPage, StatisticalArticlePage
from cms.core.query import order_by_pk_position
from cms.methodology.models import MethodologyPage
from cms.topics.services.types import ArticleDict, InternalArticleDict, MethodologyDict

if TYPE_CHECKING:
    from wagtail.query import PageQuerySet

    from ..models import TopicPage, TopicPageRelatedArticle


class BaseProcessor[T](ABC):
    """Abstract base class for processors handling related content for topic pages."""

    def __init__(self, topic_page: TopicPage, max_items_per_section: int) -> None:
        self.topic_page = topic_page
        self.max_items_per_section = max_items_per_section

    def __call__(self) -> list[T]:
        return self.process()

    @abstractmethod
    def process(self) -> list[T]:
        """Abstract method to be implemented by subclasses to return processed items."""


class RelatedArticleProcessor(BaseProcessor[ArticleDict]):
    """Processor for handling related articles for topic pages."""

    def process(self) -> list[ArticleDict]:
        """Returns a list of dictionaries representing related articles.

        Each dict has 'internal_page' pointing to a Page (or None for external) and optional 'title'.
        Manually added articles (both internal and external) are prioritised.
        """
        manual_articles, highlighted_page_pks = self._get_manual_articles()

        # If we have enough manual articles, return early
        if len(manual_articles) >= self.max_items_per_section:
            return manual_articles

        # Calculate remaining slots and fetch automatic articles
        remaining_slots = self.max_items_per_section - len(manual_articles)
        auto_articles = self._get_automatic_articles(highlighted_page_pks, remaining_slots)

        return manual_articles + auto_articles

    def _get_manual_articles(self) -> tuple[list[ArticleDict], list[int]]:
        """Extract manually configured related articles."""
        manual_articles = []
        highlighted_page_pks = []

        for related in self.topic_page.related_articles.select_related("page").all()[: self.max_items_per_section]:
            article = self._process_related_article(related)
            if article:
                manual_articles.append(article)
                if "is_external" not in article:
                    highlighted_page_pks.append(article["internal_page"].pk)

        return manual_articles, highlighted_page_pks

    def _process_related_article(self, related: TopicPageRelatedArticle) -> ArticleDict | None:
        """Process a single related article entry."""
        # Handle external articles
        if not related.page:
            if related.external_url:
                return {
                    "url": related.external_url,
                    "title": related.title,
                    "description": "",
                    "is_external": True,
                }
            return None

        # Handle internal pages
        page = related.page.specific_deferred  # type: ignore[attr-defined]

        # Skip non-live or restricted pages
        if not page.live or page.get_view_restrictions().exists():
            return None

        article_dict: InternalArticleDict = {"internal_page": page}

        if related.title:
            article_dict["title"] = related.title

        return article_dict

    def _get_automatic_articles(self, excluded_pks: Iterable[int], limit: int) -> list[ArticleDict]:
        """Return up to `limit` latest StatisticalArticlePages related to this topic."""
        excluded_pks = set(excluded_pks)

        # Collect latest article from descendant series
        descendant_series = ArticleSeriesPage.objects.descendant_of(self.topic_page).live()
        descendant_latest_pks = self._latest_article_pks_for_series(descendant_series)

        # Collect latest article PKs for other tagged series across topic pages
        descendant_series_pks = descendant_series.values_list("pk", flat=True)
        tagged_series = (
            ArticleSeriesPage.objects.live()
            .filter(topics__topic_id=self.topic_page.topic_id, locale_id=self.topic_page.locale_id)
            .exclude(pk__in=descendant_series_pks)
        )
        tagged_latest_pks = self._latest_article_pks_for_series(tagged_series)

        # Combine and fetch once with a single order and limit
        source_pks: set[int] = descendant_latest_pks | tagged_latest_pks
        if excluded_pks:
            source_pks.difference_update(excluded_pks)

        if not source_pks:
            return []

        qs = (
            StatisticalArticlePage.objects.live()
            .public()
            .filter(pk__in=source_pks)
            .defer_streamfields()
            .order_by("-release_date", "-pk")
        )

        return [{"internal_page": page} for page in qs[:limit]]

    def _latest_article_pks_for_series(self, series_qs: PageQuerySet) -> set[int]:
        """For each series in `series_qs`, return the PK of its latest StatisticalArticlePage."""
        newest_child = (
            StatisticalArticlePage.objects.live()
            .public()
            .filter(path__startswith=OuterRef("path"), depth__gte=OuterRef("depth"))
            .order_by("-release_date", "-pk")
            .values("pk")[:1]
        )

        # Annotate each series with its newest child PK, filter out nulls
        return set(
            series_qs.annotate(latest_child_pk=Subquery(newest_child))
            .exclude(latest_child_pk__isnull=True)
            .values_list("latest_child_pk", flat=True)
        )


class RelatedMethodologyProcessor(BaseProcessor[MethodologyDict]):
    """Processor for handling related methodologies for topic pages."""

    def process(self) -> list[MethodologyDict]:
        """Returns a list of dictionaries representing methodologies relevant for this topic.

        Each dict has 'internal_page' pointing to a MethodologyPage.
        Manually highlighted methodologies are prioritised and shown in their configured order.
        """
        highlighted_pages, highlighted_page_pks = self._get_manual_methodologies()
        highlighted_dicts: list[MethodologyDict] = [{"internal_page": page} for page in highlighted_pages]

        # If we have enough highlighted methodologies, return early
        if len(highlighted_pages) >= self.max_items_per_section:
            return highlighted_dicts

        # Calculate remaining slots and fetch automatic methodologies
        remaining_slots = self.max_items_per_section - len(highlighted_pages)
        auto_pages = self._get_automatic_methodologies(highlighted_page_pks, remaining_slots)

        # Combine highlighted and automatic methodologies
        return highlighted_dicts + auto_pages

    def _get_manual_methodologies(self) -> tuple[list[MethodologyPage], list[int]]:
        """Get manually highlighted methodologies in their configured order."""
        highlighted_page_pks = list(self.topic_page.related_methodologies.values_list("page_id", flat=True))[
            : self.max_items_per_section
        ]

        if not highlighted_page_pks:
            return [], []

        # Fetch pages in the order they were added
        pages = list(
            order_by_pk_position(
                MethodologyPage.objects.live().public().defer_streamfields(),
                pks=highlighted_page_pks,
                exclude_non_matches=True,
            )
        )
        return pages, highlighted_page_pks

    def _get_automatic_methodologies(self, excluded_pks: Iterable[int], limit: int) -> list[MethodologyDict]:
        """Get automatically selected methodologies based on topic relationships using a single query."""
        descendant_qs = MethodologyPage.objects.descendant_of(self.topic_page)
        descendant_condition = Q(pk__in=descendant_qs.values("pk"))
        tagged_condition = Q(topics__topic_id=self.topic_page.topic_id)

        methodologies = (
            MethodologyPage.objects.live()
            .public()
            .filter(locale=self.topic_page.locale)
            .filter(descendant_condition | tagged_condition)
            .exclude(pk__in=excluded_pks)
            .distinct()
            .order_by(Coalesce("last_revised_date", "publication_date").desc())
        )

        return [{"internal_page": page} for page in methodologies[:limit]]
