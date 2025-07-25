from datetime import datetime

from django.core.exceptions import ValidationError
from django.test import TestCase, override_settings
from django.utils.translation import gettext_lazy as _
from wagtail.blocks import StreamValue
from wagtail.coreutils import get_dummy_request
from wagtail.models import Locale

from cms.articles.tests.factories import ArticleSeriesPageFactory, StatisticalArticlePageFactory
from cms.datasets.blocks import DatasetStoryBlock
from cms.home.models import HomePage
from cms.methodology.tests.factories import MethodologyPageFactory
from cms.taxonomy.tests.factories import TopicFactory
from cms.topics.tests.factories import (
    TopicPageFactory,
    TopicPageRelatedArticleFactory,
    TopicPageRelatedMethodologyFactory,
)


class TopicPageTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.home_page = HomePage.objects.first()
        cls.topic_page = TopicPageFactory(title="Test Topic")

        # Create relevant pages
        cls.article_series = ArticleSeriesPageFactory(title="Article Series", parent=cls.topic_page)
        cls.older_article = StatisticalArticlePageFactory(
            title="Older Article", parent=cls.article_series, release_date=datetime(2024, 11, 1)
        )
        cls.article = StatisticalArticlePageFactory(
            title="Article", parent=cls.article_series, release_date=datetime(2024, 12, 1)
        )

        cls.topic_page.featured_series = cls.article_series
        cls.topic_page.save()

        cls.methodology = MethodologyPageFactory(parent=cls.topic_page, publication_date=datetime(2024, 6, 1))
        cls.another_methodology = MethodologyPageFactory(parent=cls.topic_page, publication_date=datetime(2024, 11, 1))

    def test_topic_label(self):
        self.assertEqual(self.topic_page.label, "Topic")

    def test_latest_article_in_featured_series(self):
        self.assertEqual(self.topic_page.latest_article_in_featured_series, self.article)

        another_article = StatisticalArticlePageFactory(parent=self.article_series, release_date=datetime(2025, 2, 1))
        del self.topic_page.latest_article_in_featured_series
        self.assertEqual(self.topic_page.latest_article_in_featured_series, another_article)

    def test_processed_articles_combines_highlighted_and_latest_in_series(self):
        # Create additional articles
        article_in_other_series = StatisticalArticlePageFactory(
            title="Article in other series",
            parent=ArticleSeriesPageFactory(parent=self.topic_page),
            release_date=datetime(2025, 2, 1),
        )

        TopicPageRelatedArticleFactory(parent=self.topic_page, page=self.older_article)
        self.assertListEqual(
            self.topic_page.processed_articles, [self.older_article, article_in_other_series, self.article]
        )

    def test_processed_articles_combines_highlighted_and_latest_in_series_but_not_if_same(self):
        # Create additional articles
        article_in_other_series = StatisticalArticlePageFactory(
            title="Article in other series",
            parent=ArticleSeriesPageFactory(parent=self.topic_page),
            release_date=datetime(2025, 2, 1),
        )

        TopicPageRelatedArticleFactory(parent=self.topic_page, page=self.article)
        self.assertListEqual(self.topic_page.processed_articles, [self.article, article_in_other_series])

    def test_processed_articles_shows_only_highlighted_if_all_selected(self):
        # Create additional articles
        new_article = StatisticalArticlePageFactory(parent=self.article_series)
        StatisticalArticlePageFactory(
            title="Article in other series",
            parent=ArticleSeriesPageFactory(parent=self.topic_page),
            release_date=datetime(2025, 2, 1),
        )

        TopicPageRelatedArticleFactory(parent=self.topic_page, page=self.older_article)
        TopicPageRelatedArticleFactory(parent=self.topic_page, page=new_article)
        TopicPageRelatedArticleFactory(parent=self.topic_page, page=self.article)
        self.assertListEqual(self.topic_page.processed_articles, [self.older_article, new_article, self.article])

    def test_processed_methodologies_combines_highlighted_and_child_pages(self):
        self.assertListEqual(self.topic_page.processed_methodologies, [self.another_methodology, self.methodology])

        del self.topic_page.processed_methodologies
        TopicPageRelatedMethodologyFactory(parent=self.topic_page, page=self.methodology)

        self.assertListEqual(self.topic_page.processed_methodologies, [self.methodology, self.another_methodology])

    def test_processed_methodologies_shows_only_highlighted_if_all_selected(self):
        new_methodology = MethodologyPageFactory(parent=self.topic_page, publication_date=datetime(2024, 2, 1))
        new_methodology2 = MethodologyPageFactory(parent=self.topic_page, publication_date=datetime(2023, 2, 1))

        TopicPageRelatedMethodologyFactory(parent=self.topic_page, page=self.methodology)
        TopicPageRelatedMethodologyFactory(parent=self.topic_page, page=new_methodology2)
        TopicPageRelatedMethodologyFactory(parent=self.topic_page, page=new_methodology)

        self.assertListEqual(
            self.topic_page.processed_methodologies, [self.methodology, new_methodology2, new_methodology]
        )

    def test_table_of_contents_includes_all_sections(self):
        manual_dataset = {"title": "test manual", "description": "manual description", "url": "https://example.com"}

        self.topic_page.datasets = StreamValue(DatasetStoryBlock(), stream_data=[("manual_link", manual_dataset)])

        self.assertListEqual(
            self.topic_page.table_of_contents,
            [
                {"url": "#featured", "text": "Featured"},
                {"url": "#related-articles", "text": "Related articles"},
                {"url": "#related-methods", "text": "Methods and quality information"},
                {"url": "#data", "text": "Data"},
            ],
        )

    def test_table_of_contents_without_features(self):
        self.topic_page.featured_series = None

        self.assertNotIn({"url": "#featured", "text": "Featured"}, self.topic_page.table_of_contents)

    def test_table_of_contents_without_datasets(self):
        self.topic_page.datasets = None

        self.assertNotIn({"url": "#data", "text": "Data"}, self.topic_page.table_of_contents)

    def test_table_of_contents_includes_explore_more(self):
        self.topic_page.explore_more = [("external_link", {"url": "https://example.com"})]

        toc = self.topic_page.table_of_contents
        self.assertIn({"url": "#explore-more", "text": _("Explore more")}, toc)

    def test_get_context(self):
        context = self.topic_page.get_context(get_dummy_request())

        self.assertListEqual(context["table_of_contents"], self.topic_page.table_of_contents)
        self.assertEqual(context["featured_item"], self.article)
        self.assertIn("formatted_articles", context)
        self.assertIn("formatted_methodologies", context)
        self.assertEqual(len(context["formatted_articles"]), len(self.topic_page.processed_articles))
        self.assertEqual(len(context["formatted_methodologies"]), len(self.topic_page.processed_methodologies))

    @override_settings(IS_EXTERNAL_ENV=True)
    def test_render_in_external_env(self):
        """Test that the index page renders in external environment."""
        response = self.client.get(self.topic_page.url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.article.display_title)

    def test_translated_model_taxonomy_enforcement(self):
        # Create a translations of self.topic_page
        welsh_locale = Locale.objects.get(language_code="cy")

        # This should not raise a ValidationError
        translated_topic_page = TopicPageFactory(
            title="Test Topic",
            locale=welsh_locale,
            translation_key=self.topic_page.translation_key,
            topic=self.topic_page.topic,
        )

        # Assign different topic
        translated_topic_page.topic = TopicFactory()

        with self.assertRaisesRegex(ValidationError, "The topic needs to be the same as the English page."):
            translated_topic_page.save()

    def test_headline_figures_clean(self):
        with self.assertRaisesRegex(ValidationError, "If you add headline figures, please add at least 2."):
            # Should not validate with just one
            self.topic_page.headline_figures.append(
                (
                    "figure",
                    {
                        "series": self.article_series,
                        "figure_id": "figurexyz",
                    },
                ),
            )
            self.topic_page.clean()
        # Should validate with two
        self.topic_page.headline_figures.append(
            (
                "figure",
                {
                    "series": self.article_series,
                    "figure_id": "figureabc",
                },
            ),
        )
        self.topic_page.clean()

        # Should not validate with duplicates
        with self.assertRaisesRegex(ValidationError, "Duplicate headline figures are not allowed."):
            self.topic_page.headline_figures.append(
                (
                    "figure",
                    {
                        "series": self.article_series,
                        "figure_id": "figureabc",
                    },
                ),
            )
            self.topic_page.clean()
