from typing import TYPE_CHECKING, Any, TypedDict

from django.db.models import OuterRef, Subquery
from wagtail.blocks import StreamValue

from cms.core.formatting_utils import format_as_document_list_item

if TYPE_CHECKING:
    from wagtail.query import PageQuerySet

    from .models import StatisticalArticlePage, TopicPage, TopicPageRelatedArticle


class InternalArticleDict(TypedDict, total=False):
    internal_page: "StatisticalArticlePage"
    title: str


class ExternalArticleDict(TypedDict):
    url: str
    title: str
    description: str
    is_external: bool


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

        # article_dict = {"internal_page": page}
        # if related.title:
        #     article_dict["title"] = related.title

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

    def _get_descendant_articles(self, excluded_pks: list[int]) -> list["StatisticalArticlePage"]:
        # Import here to avoid circular imports
        from cms.articles.models import (  # pylint: disable=import-outside-toplevel
            ArticleSeriesPage,
            StatisticalArticlePage,
        )

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

    def _get_topic_tagged_articles(self, excluded_pks: list[int]) -> list["StatisticalArticlePage"]:
        # Import here to avoid circular imports
        from cms.articles.models import (  # pylint: disable=import-outside-toplevel
            ArticleSeriesPage,
            StatisticalArticlePage,
        )

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
        # import here to avoid circular imports
        from .models import StatisticalArticlePage  # pylint: disable=import-outside-toplevel

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

    def _combine_and_sort_articles(
        self, *articles_lists: list["StatisticalArticlePage"]
    ) -> list["StatisticalArticlePage"]:
        """Combine articles lists and sort them by release date."""
        combined = []
        for articles in articles_lists:
            combined.extend(articles)

        combined.sort(key=lambda page: page.release_date, reverse=True)
        return combined
