from datetime import datetime
from typing import TYPE_CHECKING, TypedDict

from cms.articles.tests.factories import (
    ArticleSeriesPageFactory,
    StatisticalArticlePageFactory,
)
from cms.methodology.tests.factories import MethodologyPageFactory
from cms.taxonomy.models import GenericPageToTaxonomyTopic
from cms.taxonomy.tests.factories import TopicFactory

if TYPE_CHECKING:
    from cms.articles.models import ArticleSeriesPage, ArticlesIndexPage, StatisticalArticlePage
    from cms.methodology.models import MethodologyIndexPage, MethodologyPage
    from cms.taxonomy.models import Topic
    from cms.topics.models import TopicPage


class ArticleDataDict(TypedDict, total=False):
    series: str
    article: str
    release_date: str
    topic: str | None


class MethodologyDataDict(TypedDict, total=False):
    title: str
    methodology: str
    publication_date: str
    topic: str | None


class TopicContentBuilder:
    """Helper class to build topic page structures for tests."""

    def __init__(self) -> None:
        self.series_cache: dict[str, ArticleSeriesPage] = {}
        self.topic_cache: dict[str, Topic] = {}
        self.article_index_cache: dict[str, ArticlesIndexPage] = {}
        self.methodology_index_cache: dict[str, MethodologyIndexPage] = {}

    def _tag_page_with_topic(self, page: ArticleSeriesPage | MethodologyPage, topic: Topic) -> None:
        """Create relationship between series, methodology page and topic."""
        GenericPageToTaxonomyTopic.objects.create(page=page, topic=topic)

    def get_or_create_topic(self, topic_name: str) -> str:
        """Get existing topic or create new one."""
        if topic_name not in self.topic_cache:
            self.topic_cache[topic_name] = TopicFactory(title=topic_name)
        return self.topic_cache[topic_name]

    def _create_series(
        self, topic_page: TopicPage, series_title: str, article_index: ArticlesIndexPage | None
    ) -> ArticleSeriesPage:
        """Create an article series under the topic page."""
        if article_index is None:
            # First series - use parent__parent
            return ArticleSeriesPageFactory(
                parent__parent=topic_page,
                title=series_title,
            )
        # Subsequent series - use existing article index
        return ArticleSeriesPageFactory(
            parent=article_index,
            title=series_title,
        )

    def _create_article(self, title: str, series: ArticleSeriesPage, release_date: str) -> StatisticalArticlePage:
        """Create a statistical article."""
        release_date_obj = datetime.strptime(release_date, "%Y-%m-%d").date()
        return StatisticalArticlePageFactory(
            title=title, parent=series, release_date=release_date_obj, news_headline=""
        )

    def _create_methodology(
        self,
        title: str,
        topic_page: TopicPage,
        methodology_index: MethodologyIndexPage | None,
        publication_date: str,
    ) -> MethodologyPage:
        """Create a methodology page."""
        publication_date_obj = datetime.strptime(publication_date, "%Y-%m-%d").date()

        if methodology_index is None:
            # First methodology - use parent__parent
            return MethodologyPageFactory(
                title=title,
                parent__parent=topic_page,
                publication_date=publication_date_obj,
            )
        # Subsequent methodologies - use existing methodology index
        return MethodologyPageFactory(
            title=title,
            parent=methodology_index,
            publication_date=publication_date_obj,
        )

    def create_articles_for_topic_page(
        self, topic_page: TopicPage, articles_data: list[ArticleDataDict]
    ) -> dict[str, StatisticalArticlePage]:
        """Create articles with series under a specific topic page."""
        created_articles = {}

        # Get or create article index for this topic page
        topic_page_id = topic_page.id
        if topic_page_id not in self.article_index_cache:
            article_index = None
        else:
            article_index = self.article_index_cache[topic_page_id]

        for row in articles_data:
            series_title = row["series"]
            article_title = row["article"]
            release_date = row["release_date"]
            series_topic_name = row.get("topic", None)

            # Get or create series
            series_key = f"{topic_page_id}_{series_title}"  # Unique key per topic page

            if series_key not in self.series_cache:
                series = self._create_series(topic_page, series_title, article_index)

                # Update article index cache
                if article_index is None:
                    article_index = series.get_parent()
                    self.article_index_cache[topic_page_id] = article_index

                # Tag the series with topic
                topic = self.get_or_create_topic(series_topic_name or topic_page.topic.title)
                self._tag_page_with_topic(series, topic)

                self.series_cache[series_key] = series
            else:
                series = self.series_cache[series_key]

            # Create the article
            article = self._create_article(article_title, series, release_date)
            created_articles[article_title] = article

        return created_articles

    def create_methodologies_for_topic_page(
        self, topic_page: TopicPage, methodologies_data: list[MethodologyDataDict]
    ) -> dict[str, MethodologyPage]:
        """Create methodologies under a specific topic page."""
        created_methodologies = {}

        # Get or create methodology index for this topic page
        topic_page_id = topic_page.id
        if topic_page_id not in self.methodology_index_cache:
            methodology_index = None
        else:
            methodology_index = self.methodology_index_cache[topic_page_id]

        for row in methodologies_data:
            methodology_title = row.get("title")
            publication_date = row["publication_date"]
            topic_name = row.get("topic")

            # Create the methodology
            methodology = self._create_methodology(methodology_title, topic_page, methodology_index, publication_date)

            # Update methodology index cache
            if methodology_index is None:
                methodology_index = methodology.get_parent()
                self.methodology_index_cache[topic_page_id] = methodology_index

            # Tag the methodology with topic if specified
            if topic_name:
                topic = self.get_or_create_topic(topic_name)
                self._tag_page_with_topic(methodology, topic)

            created_methodologies[methodology_title] = methodology

        return created_methodologies
