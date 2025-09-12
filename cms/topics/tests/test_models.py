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
from cms.methodology.tests.factories import MethodologyIndexPageFactory, MethodologyPageFactory
from cms.taxonomy.tests.factories import TopicFactory
from cms.topics.blocks import TimeSeriesPageStoryBlock
from cms.topics.models import TopicPage, TopicPageRelatedArticle, TopicPageRelatedMethodology
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
        expected = [
            {"internal_page": self.older_article},
            {"internal_page": article_in_other_series},
            {"internal_page": self.article},
        ]
        self.assertListEqual(self.topic_page.processed_articles, expected)

    def test_processed_articles_combines_highlighted_and_latest_in_series_but_not_if_same(self):
        # Create additional articles
        article_in_other_series = StatisticalArticlePageFactory(
            title="Article in other series",
            parent=ArticleSeriesPageFactory(parent=self.article_series.get_parent()),
            release_date=datetime(2025, 2, 1),
        )

        TopicPageRelatedArticleFactory(parent=self.topic_page, page=self.article)
        expected = [{"internal_page": self.article}, {"internal_page": article_in_other_series}]
        self.assertListEqual(self.topic_page.processed_articles, expected)

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
        expected = [
            {"internal_page": self.older_article},
            {"internal_page": new_article},
            {"internal_page": self.article},
        ]
        self.assertListEqual(self.topic_page.processed_articles, expected)

    def test_processed_articles_with_one_external_link(self):
        """Test that external link appears first, followed by auto-populated articles."""
        # Create additional article for auto-population
        article_in_other_series = StatisticalArticlePageFactory(
            title="Article in other series",
            parent=ArticleSeriesPageFactory(parent=self.topic_page),
            release_date=datetime(2025, 2, 1),
        )

        # Add one external link
        TopicPageRelatedArticleFactory(
            parent=self.topic_page,
            page=None,
            external_url="https://external-example.com",
            title="External Article",
        )

        processed = self.topic_page.processed_articles
        self.assertEqual(len(processed), 3)

        # First item should be the external link
        self.assertIsInstance(processed[0], dict)
        self.assertEqual(processed[0]["url"], "https://external-example.com")
        self.assertEqual(processed[0]["title"], "External Article")
        self.assertTrue(processed[0]["is_external"])

        # Remaining should be auto-populated articles
        self.assertEqual(processed[1], {"internal_page": article_in_other_series})
        self.assertEqual(processed[2], {"internal_page": self.article})

    def test_processed_articles_with_three_external_links(self):
        """Test that only the three manually added external links are returned."""
        # Add three external links
        for i in range(3):
            TopicPageRelatedArticleFactory(
                parent=self.topic_page,
                page=None,
                external_url=f"https://external-example-{i}.com",
                title=f"External Article {i}",
            )

        processed = self.topic_page.processed_articles
        self.assertEqual(len(processed), 3)

        # All should be external links
        for i, item in enumerate(processed):
            self.assertIsInstance(item, dict)
            self.assertEqual(item["url"], f"https://external-example-{i}.com")
            self.assertEqual(item["title"], f"External Article {i}")
            self.assertTrue(item["is_external"])

    def test_processed_articles_with_mixed_manual_links(self):
        """Test mix of internal page and external link appear first, followed by auto-populated."""
        # Create additional article for auto-population
        article_in_other_series = StatisticalArticlePageFactory(
            title="Article in other series",
            parent=ArticleSeriesPageFactory(parent=self.topic_page),
            release_date=datetime(2025, 2, 1),
        )

        # Add one internal page manually
        TopicPageRelatedArticleFactory(parent=self.topic_page, page=self.older_article)

        # Add one external link
        TopicPageRelatedArticleFactory(
            parent=self.topic_page,
            page=None,
            external_url="https://external-example.com",
            title="External Article",
        )

        processed = self.topic_page.processed_articles
        self.assertEqual(len(processed), 3)

        # First should be the internal page
        self.assertEqual(processed[0], {"internal_page": self.older_article})

        # Second should be the external link
        self.assertIsInstance(processed[1], dict)
        self.assertEqual(processed[1]["url"], "https://external-example.com")
        self.assertEqual(processed[1]["title"], "External Article")
        self.assertTrue(processed[1]["is_external"])

        # Third should be auto-populated (not self.article since older_article was manually selected)
        self.assertEqual(processed[2], {"internal_page": article_in_other_series})

    def test_processed_articles_with_custom_title(self):
        """Test that custom title is included when provided for internal pages."""
        TopicPageRelatedArticleFactory(parent=self.topic_page, page=self.older_article, title="Custom Article Title")

        processed = self.topic_page.processed_articles
        self.assertEqual(len(processed), 2)

        # First should be the highlighted article with custom title
        expected_first = {"internal_page": self.older_article, "title": "Custom Article Title"}
        self.assertEqual(processed[0], expected_first)

        # Second should be auto-populated without custom title
        self.assertEqual(processed[1], {"internal_page": self.article})

    def test_processed_methodologies_combines_highlighted_and_child_pages(self):
        expected = [{"internal_page": self.another_methodology}, {"internal_page": self.methodology}]
        self.assertListEqual(self.topic_page.processed_methodologies, expected)

        del self.topic_page.processed_methodologies
        TopicPageRelatedMethodologyFactory(parent=self.topic_page, page=self.methodology)

        expected_with_highlight = [{"internal_page": self.methodology}, {"internal_page": self.another_methodology}]
        self.assertListEqual(self.topic_page.processed_methodologies, expected_with_highlight)

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

        expected = [
            {"internal_page": self.methodology},
            {"internal_page": new_methodology2},
            {"internal_page": new_methodology},
        ]
        self.assertListEqual(self.topic_page.processed_methodologies, expected)

    def test_table_of_contents_includes_all_sections(self):
        manual_dataset = {"title": "test manual", "description": "manual description", "url": "https://example.com"}

        self.topic_page.datasets = StreamValue(DatasetStoryBlock(), stream_data=[("manual_link", manual_dataset)])

        self.assertListEqual(
            self.topic_page.table_of_contents,
            [
                {
                    "url": "#featured",
                    "text": "Featured",
                    "attributes": {
                        "data-ga-event": "navigation-onpage",
                        "data-ga-navigation-type": "table-of-contents",
                        "data-ga-section-title": "Featured",
                    },
                },
                {
                    "url": "#related-articles",
                    "text": "Related articles",
                    "attributes": {
                        "data-ga-event": "navigation-onpage",
                        "data-ga-navigation-type": "table-of-contents",
                        "data-ga-section-title": "Related articles",
                    },
                },
                {
                    "url": "#related-methods",
                    "text": "Methods and quality information",
                    "attributes": {
                        "data-ga-event": "navigation-onpage",
                        "data-ga-navigation-type": "table-of-contents",
                        "data-ga-section-title": "Methods and quality information",
                    },
                },
                {
                    "url": "#data",
                    "text": "Data",
                    "attributes": {
                        "data-ga-event": "navigation-onpage",
                        "data-ga-navigation-type": "table-of-contents",
                        "data-ga-section-title": "Data",
                    },
                },
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
        self.assertIn(
            {
                "url": "#explore-more",
                "text": _("Explore more"),
                "attributes": {
                    "data-ga-event": "navigation-onpage",
                    "data-ga-navigation-type": "table-of-contents",
                    "data-ga-section-title": _("Explore more"),
                },
            },
            toc,
        )

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
                    "time_series": streamfield([]),
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

    def test_get_analytics_values(self):
        analytics_values = self.topic_page.get_analytics_values(get_dummy_request())
        self.assertEqual(analytics_values["pageTitle"], self.topic_page.title)
        self.assertEqual(analytics_values["contentType"], self.topic_page.analytics_content_type)
        self.assertEqual(analytics_values["contentGroup"], self.topic_page.analytics_content_group)
        self.assertEqual(analytics_values["contentTheme"], self.topic_page.analytics_content_theme)


class TopicPageRelatedArticleValidationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.home_page = HomePage.objects.first()
        cls.topic_page = TopicPageFactory(title="Test Topic")
        cls.article = StatisticalArticlePageFactory(title="Test Article", parent=cls.topic_page)

    def test_validation_error_both_page_and_external_url_provided(self):
        """Test that ValidationError is raised if both page and external_url are provided."""
        related_article = TopicPageRelatedArticleFactory.build(
            parent=self.topic_page, page=self.article, external_url="https://example.com", title="External Title"
        )
        with self.assertRaisesRegex(
            ValidationError, "Please select either an internal page or provide an external URL, not both."
        ):
            related_article.clean()

    def test_validation_error_neither_page_nor_external_url_provided(self):
        """Test that ValidationError is raised if neither page nor external_url is provided."""
        related_article = TopicPageRelatedArticleFactory.build(
            parent=self.topic_page, page=None, external_url="", title=""
        )
        with self.assertRaisesRegex(ValidationError, "You must select an internal page or provide an external URL."):
            related_article.clean()

    def test_validation_error_external_url_without_title(self):
        """Test that ValidationError is raised if external_url is provided without a title."""
        related_article = TopicPageRelatedArticleFactory.build(
            parent=self.topic_page, page=None, external_url="https://example.com", title=""
        )
        with self.assertRaisesRegex(ValidationError, "This field is required when providing an external URL."):
            related_article.clean()

    def test_validation_passes_with_only_page(self):
        """Test that validation passes with only a page."""
        related_article = TopicPageRelatedArticleFactory.build(
            parent=self.topic_page, page=self.article, external_url="", title=""
        )
        # Should not raise ValidationError
        related_article.clean()

    def test_validation_passes_with_external_url_and_title(self):
        """Test that validation passes with an external_url and title."""
        related_article = TopicPageRelatedArticleFactory.build(
            parent=self.topic_page, page=None, external_url="https://example.com", title="External Article Title"
        )
        # Should not raise ValidationError
        related_article.clean()


class TopicPageSearchListingPagesTests(WagtailTestUtils, TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.topic_page = TopicPageFactory()

    # Related publications (statistical articles)

    def test_articles_search_link_comes_up_when_child_articles_exist(self):
        """Check that the 'View all related articles' link appears when there are child article pages."""
        article_series_page = ArticleSeriesPageFactory(parent=self.topic_page)
        article_page = StatisticalArticlePageFactory(parent=article_series_page)

        topic_page_context = self.topic_page.get_context(get_dummy_request())
        self.assertIn("related_articles", topic_page_context["search_page_urls"])
        self.assertEqual(self.topic_page.processed_articles[0]["internal_page"], article_page)

        response = self.client.get(self.topic_page.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Related articles")
        self.assertContains(response, "View all related articles")

    def test_articles_search_link_comes_up_when_highlighted_articles_are_selected(self):
        """Check that the 'View all related articles' link appears when there are highlighted article pages."""
        article_page = StatisticalArticlePageFactory()
        TopicPageRelatedArticle.objects.create(parent=self.topic_page, page=article_page)

        topic_page_context = self.topic_page.get_context(get_dummy_request())
        self.assertIn("related_articles", topic_page_context["search_page_urls"])

        response = self.client.get(self.topic_page.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Related articles")
        self.assertContains(response, "View all related articles")

    def test_articles_search_link_doesnt_come_up_when_no_child_or_highlighted_articles(self):
        """Check that the link to search pages for articles isn't present
        when there are no child or highlighted articles.
        """
        # Note - no child or related articles

        topic_page_context = self.topic_page.get_context(get_dummy_request())
        self.assertNotIn("related_articles", topic_page_context["search_page_urls"])

        response = self.client.get(self.topic_page.url)
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Related articles")
        self.assertNotContains(response, "View all related articles")

    # Related methodologies

    def test_methodologies_search_link_comes_up_when_child_methodologies_exist(self):
        """Check that the "View all related methodology" comes up when there are child methodology pages."""
        methodology_index_page = MethodologyIndexPageFactory(parent=self.topic_page)
        methodology_page = MethodologyPageFactory(parent=methodology_index_page)

        topic_page_context = self.topic_page.get_context(get_dummy_request())
        self.assertIn("related_methodologies", topic_page_context["search_page_urls"])
        self.assertEqual(self.topic_page.processed_methodologies[0]["internal_page"], methodology_page)

        response = self.client.get(self.topic_page.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Methods and quality information")
        self.assertContains(response, methodology_page.title)
        self.assertContains(response, "View all related methodology")

    def test_methodologies_search_link_comes_up_when_highlighted_methodologies_are_selected(self):
        """Check that the "View all related methodology" comes up when there are highlighted methodology pages."""
        methodology_page = MethodologyPageFactory()
        TopicPageRelatedMethodology.objects.create(parent=self.topic_page, page=methodology_page)

        topic_page_context = self.topic_page.get_context(get_dummy_request())
        self.assertIn("related_methodologies", topic_page_context["search_page_urls"])

        response = self.client.get(self.topic_page.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Methods and quality information")
        self.assertContains(response, methodology_page.title)
        self.assertContains(response, "View all related methodology")

    def test_methodologies_search_link_doesnt_come_up_when_no_child_or_highlighted_methodologies(self):
        """Check that the link to search pages for methodology pages isn't present
        when there are no child or highlighted methodology pages.
        """
        # Note - no child or related methodologies

        topic_page_context = self.topic_page.get_context(get_dummy_request())
        self.assertNotIn("related_methodologies", topic_page_context["search_page_urls"])

        response = self.client.get(self.topic_page.url)
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Methods and quality information")
        self.assertNotContains(response, "View all related methodology")

    # Related datasets

    def test_related_dataset_link_comes_up_when_dataset_section_is_present(self):
        """Test that the 'View all related data' links appears
        when there is at least one dataset in the datasets section.
        """
        self.topic_page.datasets = StreamValue(
            DatasetStoryBlock(),
            stream_data=[
                (
                    "manual_link",
                    {
                        "title": "Test dataset",
                        "description": "Test description",
                        "url": "https://example.com",
                    },
                )
            ],
        )
        self.topic_page.save()

        page_context = self.topic_page.get_context(get_dummy_request())
        self.assertIn("related_data", page_context["search_page_urls"])

        response = self.client.get(self.topic_page.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Data")
        self.assertContains(response, "Test dataset")
        self.assertContains(response, "View all related data")

    def test_related_dataset_link_does_not_come_up_when_datasets_section_not_present(self):
        """Test that the 'View all related data' links does not appear
        and the link to search page isn't included in the context
        when there are no datasets in the datasets section.
        """
        self.topic_page.datasets = None
        self.topic_page.save()

        page_context = self.topic_page.get_context(get_dummy_request())
        self.assertNotIn("related_data", page_context["search_page_urls"])

        response = self.client.get(self.topic_page.url)
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Data")
        self.assertNotContains(response, "View all related data")

    # Related time series

    def test_related_time_series_link_comes_up_when_time_series_section_is_present(self):
        """Test that the 'See more related time series' links appears
        when there is at least one time series in the time series section.
        """
        self.topic_page.time_series = StreamValue(
            TimeSeriesPageStoryBlock(),
            stream_data=[
                (
                    "time_series_page_link",
                    {
                        "title": "Test time series",
                        "description": "Test description",
                        "url": "https://example.com",
                    },
                )
            ],
        )
        self.topic_page.save()

        page_context = self.topic_page.get_context(get_dummy_request())
        self.assertIn("related_time_series", page_context["search_page_urls"])

        response = self.client.get(self.topic_page.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Time series")
        self.assertContains(response, "Test time series")
        self.assertContains(response, "View all related time series")

    def test_related_time_series_link_does_not_come_up_when_time_series_section_not_present(self):
        """Test that the 'See more related time series' links does not appear
        and the link to search page isn't included in the context
        when there are no time series in the time series section.
        """
        self.topic_page.time_series = None
        self.topic_page.save()

        page_context = self.topic_page.get_context(get_dummy_request())
        self.assertNotIn("related_time_series", page_context["search_page_urls"])

        response = self.client.get(self.topic_page.url)
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Time Series")
        self.assertNotContains(response, "View all related time series")
