from datetime import datetime

from django.core.exceptions import ValidationError
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from wagtail.blocks import StreamValue
from wagtail.coreutils import get_dummy_request
from wagtail.models import Locale
from wagtail.test.utils import WagtailTestUtils
from wagtail.test.utils.form_data import inline_formset, nested_form_data, rich_text, streamfield

from cms.articles.tests.factories import ArticleSeriesPageFactory, StatisticalArticlePageFactory
from cms.datasets.blocks import DatasetStoryBlock
from cms.home.models import HomePage
from cms.methodology.tests.factories import MethodologyPageFactory
from cms.taxonomy.tests.factories import TopicFactory
from cms.topics.models import TopicPage
from cms.topics.tests.factories import (
    TopicPageFactory,
    TopicPageRelatedArticleFactory,
    TopicPageRelatedMethodologyFactory,
)


class TopicPageTestCase(WagtailTestUtils, TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.superuser = cls.create_superuser(username="superuser")
        cls.home_page = HomePage.objects.first()
        cls.topic_page = TopicPageFactory(title="Test Topic")

        # Create relevant pages
        cls.article_series = ArticleSeriesPageFactory(title="Article Series", parent__parent=cls.topic_page)
        cls.older_article = StatisticalArticlePageFactory(
            title="Older Article", parent=cls.article_series, release_date=datetime(2024, 11, 1)
        )
        cls.article = StatisticalArticlePageFactory(
            title="Article", parent=cls.article_series, release_date=datetime(2024, 12, 1)
        )

        cls.topic_page.featured_series = cls.article_series
        cls.topic_page.save(update_fields=["featured_series"])

        cls.methodology = MethodologyPageFactory(parent__parent=cls.topic_page, publication_date=datetime(2024, 6, 1))
        cls.another_methodology = MethodologyPageFactory(
            parent=cls.methodology.get_parent(), publication_date=datetime(2024, 11, 1)
        )

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
            parent=ArticleSeriesPageFactory(parent=self.article_series.get_parent()),
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
            parent=ArticleSeriesPageFactory(parent=self.article_series.get_parent()),
            release_date=datetime(2025, 2, 1),
        )

        TopicPageRelatedArticleFactory(parent=self.topic_page, page=self.article)
        self.assertListEqual(self.topic_page.processed_articles, [self.article, article_in_other_series])

    def test_processed_articles_shows_only_highlighted_if_all_selected(self):
        # Create additional articles
        new_article = StatisticalArticlePageFactory(parent=self.article_series)
        StatisticalArticlePageFactory(
            title="Article in other series",
            parent=ArticleSeriesPageFactory(parent=self.article_series.get_parent()),
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
        new_methodology = MethodologyPageFactory(
            parent=self.methodology.get_parent(), publication_date=datetime(2024, 2, 1)
        )
        new_methodology2 = MethodologyPageFactory(
            parent=self.methodology.get_parent(), publication_date=datetime(2023, 2, 1)
        )

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
        welsh_homepage = self.home_page.copy_for_translation(locale=welsh_locale)

        # This should not raise a ValidationError
        translated_topic_page = TopicPageFactory(
            title="Test Topic",
            locale=welsh_locale,
            parent=welsh_homepage,
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

    def test_cannot_add_children_once_articles_and_methodologies_index_are_created(self):
        self.assertEqual(TopicPage.objects.count(), 1)
        self.client.force_login(self.superuser)
        response = self.client.post(
            reverse("wagtailadmin_pages:add", args=("topics", "topicpage", self.home_page.pk)),
            nested_form_data(
                {
                    "title": "Fresh topic",
                    "slug": "new-topic",
                    "summary": rich_text("Summary"),
                    "featured_series": "",
                    "related_articles": inline_formset([]),
                    "related_methodologies": inline_formset([]),
                    "explore_more": streamfield([]),
                    "headline_figures": streamfield([]),
                    "datasets": streamfield([]),
                    "topic": TopicFactory().pk,
                }
            ),
        )
        topics_qs = TopicPage.objects.child_of(self.home_page)
        self.assertEqual(topics_qs.count(), 2)
        new_topic_page = topics_qs.filter(title="Fresh topic").first()

        self.assertFalse(new_topic_page.permissions_for_user(self.superuser).can_add_subpage())

        response = self.client.get(reverse("wagtailadmin_explore", args=[new_topic_page.pk]))
        self.assertContains(response, "/new-topic/articles/")
        self.assertContains(response, "/new-topic/methodologies/")

        # Should have 2 "add child page" links, one each for articles and methodologies index
        self.assertContains(response, "Add child page", 2)
        self.assertNotContains(response, reverse("wagtailadmin_pages:add_subpage", args=[new_topic_page.pk]))

        new_topic_page.get_children().first().delete()
        self.assertTrue(new_topic_page.permissions_for_user(self.superuser).can_add_subpage())
        response = self.client.get(reverse("wagtailadmin_explore", args=[new_topic_page.pk]))
        self.assertContains(response, "Add child page", 3)
        self.assertContains(response, reverse("wagtailadmin_pages:add_subpage", args=[new_topic_page.pk]))
