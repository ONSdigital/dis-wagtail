from abc import ABC, abstractmethod
from collections.abc import Iterable
from typing import TYPE_CHECKING, Protocol, cast

from django.db.models import OuterRef, Q, Subquery
from django.db.models.functions import Coalesce

from cms.articles.models import ArticleSeriesPage, StatisticalArticlePage
from cms.methodology.models import MethodologyPage
from cms.topics.services.types import (
    ArticleDict,
    ExternalArticleDict,
    InternalArticleDict,
    InternalMethodologyDict,
    MethodologyDict,
)

from ...core.enums import RelatedContentType

if TYPE_CHECKING:
    from wagtail.query import PageQuerySet

    from ..models import TopicPage


class BaseRelatedItem(Protocol):
    page: object | None
    external_url: str
    title: str


class MethodologyRelatedItem(BaseRelatedItem, Protocol):
    content_type: object | None


class BaseProcessor[T, R: BaseRelatedItem](ABC):
    """Abstract base class for processors handling related content for topic pages."""

    manual_relation_name: str

    def __init__(self, topic_page: TopicPage, max_items_per_section: int) -> None:
        self.topic_page = topic_page
        self.max_items_per_section = max_items_per_section

    def __call__(self) -> list[T]:
        return self.process()

    def process(self) -> list[T]:
        """Build a section list by combining manual items and automatic top-up items."""
        manual_pages, highlighted_page_pks = self._get_manual_pages()

        if len(manual_pages) >= self.max_items_per_section:
            return manual_pages

        remaining_slots = self.max_items_per_section - len(manual_pages)
        auto_pages = self._get_automatic_pages(highlighted_page_pks, remaining_slots)

        return manual_pages + auto_pages

    @abstractmethod
    def _get_automatic_pages(self, excluded_pks: Iterable[int], limit: int) -> list[T]:
        """Return automatic items, excluding selected internal page PKs."""

    @abstractmethod
    def _process_related(self, related: R) -> T | None:
        """Transform a related object into a display item or return None to skip it."""

    def _get_manual_pages(self) -> tuple[list[T], list[int]]:
        """Collect manual related items and track highlighted internal page PKs."""
        manual_items: list[T] = []
        highlighted_page_pks: list[int] = []

        related_manager = getattr(self.topic_page, self.manual_relation_name)
        related_items = cast(Iterable[R], related_manager.select_related("page").all()[: self.max_items_per_section])
        for related in related_items:
            item = self._process_related(related)
            if not item:
                continue

            manual_items.append(item)

            if isinstance(item, dict) and not item.get("is_external"):
                internal_page = item.get("internal_page")
                if internal_page:
                    highlighted_page_pks.append(internal_page.pk)

        return manual_items, highlighted_page_pks


class RelatedArticleProcessor(BaseProcessor[ArticleDict, BaseRelatedItem]):
    """Processor for handling related articles for topic pages."""

    manual_relation_name = "related_articles"

    def _process_related(self, related: BaseRelatedItem) -> ArticleDict | None:
        """Process a single related article entry."""
        # Handle external articles
        if not related.page:
            if related.external_url:
                external_article: ExternalArticleDict = {
                    "url": related.external_url,
                    "title": related.title,
                    "description": "",
                    "content_type": RelatedContentType.ARTICLE,
                    "is_external": True,
                }
                return external_article
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

    def _get_automatic_pages(self, excluded_pks: Iterable[int], limit: int) -> list[ArticleDict]:
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

        auto_articles: list[ArticleDict] = []
        for page in qs[:limit]:
            auto_articles.append({"internal_page": page})
        return auto_articles

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


class RelatedMethodologyProcessor(BaseProcessor[MethodologyDict, MethodologyRelatedItem]):
    """Processor for handling related methodologies for topic pages."""

    manual_relation_name = "related_methodologies"

    def _process_related(self, related: MethodologyRelatedItem) -> MethodologyDict | None:
        if not related.page:
            if related.external_url:
                external_methodology: ExternalArticleDict = {
                    "url": related.external_url,
                    "title": related.title,
                    "description": "",
                    "content_type": cast(RelatedContentType, related.content_type),
                    "is_external": True,
                }
                return external_methodology
            return None

        page = related.page.specific_deferred  # type: ignore[attr-defined]

        # Skip non-live or restricted pages
        if not page.live or page.get_view_restrictions().exists():
            return None

        methodology_dict: InternalMethodologyDict = {"internal_page": page}
        if related.title:
            methodology_dict["title"] = related.title

        return methodology_dict

    def _get_automatic_pages(self, excluded_pks: Iterable[int], limit: int) -> list[MethodologyDict]:
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

        auto_methodologies: list[MethodologyDict] = []
        for page in methodologies[:limit]:
            auto_methodologies.append({"internal_page": page})
        return auto_methodologies
