from typing import TYPE_CHECKING, Any, TypedDict

from django.db.models import OuterRef, Subquery
from wagtail.blocks import StreamValue

from cms.articles.models import ArticleSeriesPage, StatisticalArticlePage
from cms.core.formatting_utils import format_as_document_list_item
from cms.core.query import order_by_pk_position
from cms.methodology.models import MethodologyPage

if TYPE_CHECKING:
    from wagtail.query import PageQuerySet

    from .models import TopicPage, TopicPageRelatedArticle


class InternalArticleDict(TypedDict, total=False):
    internal_page: "StatisticalArticlePage"
    title: str


class ExternalArticleDict(TypedDict):
    url: str
    title: str
    description: str
    is_external: bool


class MethodologyDict(TypedDict):
    internal_page: MethodologyPage


ArticleDict = InternalArticleDict | ExternalArticleDict


def format_time_series_as_document_list(time_series: StreamValue) -> list[dict[str, Any]]:
    """Takes a StreamValue of time series blocks (the value of a StreamField of TimeSeriesStoryBlock).

    Returns the time series in a list of dictionaries in the format required for the ONS Document List design system
    component.
    See: https://service-manual.ons.gov.uk/design-system/components/document-list
    """
    time_series_documents: list = []

    for time_series_block in time_series:
        block_value = time_series_block.value
        time_series_document = format_as_document_list_item(
            title=block_value["title"],
            url=block_value["url"],
            content_type="Time series",
            description=block_value["description"],
        )

        time_series_documents.append(time_series_document)

    return time_series_documents


class ArticleProcessor:
    """Service class for processing related articles for topic pages."""

    def __init__(self, topic_page: "TopicPage", max_items_per_section: int) -> None:
        self.topic_page = topic_page
        self.max_items_per_section = max_items_per_section

    def get_processed_articles(self) -> list[ArticleDict]:
        """Returns a list of dictionaries representing related articles.

        Each dict has 'internal_page' pointing to a Page (or None for external) and optional 'title'.
        Manually added articles (both internal and external) are prioritised.
        """
        manual_articles, highlighted_page_pks = self._get_manual_articles()

        # If we have enough manual articles, return early
        if len(manual_articles) >= self.max_items_per_section:
            return manual_articles[: self.max_items_per_section]

        # Calculate remaining slots and fetch automatic articles
        remaining_slots = self.max_items_per_section - len(manual_articles)
        auto_articles = self._get_automatic_articles(highlighted_page_pks, remaining_slots)

        return manual_articles + auto_articles

    def _get_manual_articles(self) -> tuple[list[ArticleDict], list[int]]:
        """Extract manually configured related articles."""
        manual_articles = []
        highlighted_page_pks = []

        for related in self.topic_page.related_articles.select_related("page").all():
            article = self._process_related_article(related)
            if article:
                manual_articles.append(article)
                if "is_external" not in article:
                    highlighted_page_pks.append(article["internal_page"].pk)

        return manual_articles, highlighted_page_pks

    def _process_related_article(self, related: "TopicPageRelatedArticle") -> ArticleDict | None:
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

    def _get_automatic_articles(self, excluded_pks: list[int], limit: int) -> list[ArticleDict]:
        """Get automatically selected articles based on topic relationships."""
        # Get articles from descendant series
        descendant_articles = self._get_descendant_articles(excluded_pks)

        # Get articles from topic-tagged series across the CMS
        tagged_articles = self._get_topic_tagged_articles(excluded_pks)

        # Combine and sort by release date
        combined_articles = self._combine_and_sort_articles(descendant_articles, tagged_articles)

        # Convert to dict format and apply limit
        return [{"internal_page": page} for page in combined_articles[:limit]]

    def _get_descendant_articles(self, excluded_pks: list[int]) -> list[StatisticalArticlePage]:
        descendant_series = ArticleSeriesPage.objects.descendant_of(self.topic_page)
        latest_pks = self._get_latest_articles_by_series(descendant_series)

        # Get the latest articles under this topic page (topic page -> articles index -> article series page ->
        # latest stats article page), excluding those already highlighted
        return list(
            StatisticalArticlePage.objects.filter(pk__in=latest_pks)
            .exclude(pk__in=excluded_pks)
            .live()
            .public()
            .defer_streamfields()
            .order_by("-release_date")
        )

    def _get_topic_tagged_articles(self, excluded_pks: list[int]) -> list[StatisticalArticlePage]:
        # Get descendant series PKs to exclude
        descendant_series_pks = set(
            ArticleSeriesPage.objects.descendant_of(self.topic_page).values_list("pk", flat=True)
        )

        # Get all other article series across the CMS that are tagged with this topic of this topic page
        # (excluding descendants)
        tagged_series = (
            ArticleSeriesPage.objects.live()
            .public()
            .filter(topics__topic_id=self.topic_page.topic_id)
            .exclude(pk__in=descendant_series_pks)
        )

        latest_pks = self._get_latest_articles_by_series(tagged_series)

        # Get the latest articles, excluding those already highlighted
        return list(
            StatisticalArticlePage.objects.filter(pk__in=latest_pks)
            .filter(locale=self.topic_page.locale)  # Ensure articles are in the same locale as the topic page
            .exclude(pk__in=excluded_pks)
            .live()
            .public()
            .defer_streamfields()
            .order_by("-release_date")
        )

    def _get_latest_articles_by_series(self, series_qs: "PageQuerySet") -> list[int]:
        """Get the PK of the latest article for each series."""
        # Subquery to find the latest article that is a descendant of each series
        newest_qs = (
            StatisticalArticlePage.objects.live()
            .public()
            .filter(path__startswith=OuterRef("path"), depth__gte=OuterRef("depth"))
            .order_by("-release_date")
        )

        return list(
            series_qs.annotate(latest_child_page=Subquery(newest_qs.values("pk")[:1])).values_list(
                "latest_child_page", flat=True
            )
        )

    def _combine_and_sort_articles(self, *articles_lists: list[StatisticalArticlePage]) -> list[StatisticalArticlePage]:
        """Combine articles lists and sort them by release date."""
        combined = []
        for articles in articles_lists:
            combined.extend(articles)

        combined.sort(key=lambda page: page.release_date, reverse=True)
        return combined


class MethodologyProcessor:
    """Service class for processing related methodologies for topic pages."""

    def __init__(self, topic_page: "TopicPage", max_items_per_section: int) -> None:
        self.topic_page = topic_page
        self.max_items_per_section = max_items_per_section

    def get_processed_methodologies(self) -> list[MethodologyDict]:
        """Returns a list of dictionaries representing methodologies relevant for this topic.

        Each dict has 'internal_page' pointing to a MethodologyPage.
        Manually highlighted methodologies are prioritised and shown in their configured order.
        """
        highlighted_pages = self._get_highlighted_methodologies()

        # If we have enough highlighted methodologies, return early
        if len(highlighted_pages) >= self.max_items_per_section:
            result: list[MethodologyDict] = [
                {"internal_page": page} for page in highlighted_pages[: self.max_items_per_section]
            ]
            return result

        # Calculate remaining slots and fetch automatic methodologies
        remaining_slots = self.max_items_per_section - len(highlighted_pages)
        highlighted_pages_pks = [page.pk for page in highlighted_pages]
        auto_pages = self._get_automatic_methodologies(highlighted_pages_pks, remaining_slots)

        # Combine highlighted and automatic methodologies
        highlighted_dicts: list[MethodologyDict] = [{"internal_page": page} for page in highlighted_pages]

        return [*highlighted_dicts, *auto_pages]

    def _get_highlighted_methodologies(self) -> list[MethodologyPage]:
        """Get manually highlighted methodologies in their configured order."""
        highlighted_page_pks = tuple(
            page_id for page_id in self.topic_page.related_methodologies.values_list("page_id", flat=True)
        )

        if not highlighted_page_pks:
            return []

        # Fetch pages in the order they were added
        return list(
            order_by_pk_position(
                MethodologyPage.objects.live().public().defer_streamfields(),
                pks=highlighted_page_pks,
                exclude_non_matches=True,
            )
        )

    def _get_automatic_methodologies(self, excluded_pks: list[int], limit: int) -> list[MethodologyDict]:
        """Get automatically selected methodologies based on topic relationships."""
        # Get methodologies from descendants of this topic page
        descendant_methodologies = self._get_descendant_methodologies(excluded_pks)

        # Get methodologies tagged with this topic from across the CMS
        tagged_methodologies = self._get_topic_tagged_methodologies(excluded_pks)

        # Combine and sort by last revised date
        combined_methodologies = self._combine_and_sort_methodologies(descendant_methodologies, tagged_methodologies)

        # Convert to dict format and apply limit
        result: list[MethodologyDict] = [{"internal_page": page} for page in combined_methodologies[:limit]]
        return result

    def _get_descendant_methodologies(self, excluded_pks: list[int]) -> list[MethodologyPage]:
        """Get methodology pages that are descendants of this topic page."""
        return list(
            MethodologyPage.objects.descendant_of(self.topic_page)
            .exclude(pk__in=excluded_pks)
            .live()
            .public()
            .order_by("-last_revised_date")
        )

    def _get_topic_tagged_methodologies(self, excluded_pks: list[int]) -> list[MethodologyPage]:
        """Get methodology pages tagged with this topic but not descendants of this topic page."""
        descendant_methodology_pks = set(
            MethodologyPage.objects.descendant_of(self.topic_page).values_list("pk", flat=True)
        )

        # Get methodologies tagged with this topic from across the CMS
        return list(
            MethodologyPage.objects.live()
            .filter(locale=self.topic_page.locale)  # Ensure methodologies are in the same locale as the topic page
            .public()
            .filter(topics__topic_id=self.topic_page.topic_id)
            .exclude(pk__in=descendant_methodology_pks)
            .exclude(pk__in=excluded_pks)
            .order_by("-last_revised_date")
        )

    def _combine_and_sort_methodologies(self, *methodology_lists: list[MethodologyPage]) -> list[MethodologyPage]:
        """Combine methodologies lists and sort them by last revised date."""
        combined = []
        for methodologies in methodology_lists:
            combined.extend(methodologies)

        # Sort by last_revised date, falling back to publication_date if not available
        combined.sort(key=lambda page: page.last_revised_date or page.publication_date, reverse=True)

        return combined
