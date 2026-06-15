from datetime import datetime
from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from wagtail.models import PageLogEntry
from wagtail.test.utils import WagtailTestUtils

from cms.articles.tests.factories import ArticleSeriesPageFactory, StatisticalArticlePageFactory
from cms.core.tests.utils import rebuild_internal_search_index
from cms.methodology.tests.factories import MethodologyPageFactory
from cms.topics.tests.factories import TopicPageFactory
from cms.topics.viewsets import (
    featured_series_page_chooser_viewset,
    highlighted_article_page_chooser_viewset,
    highlighted_methodology_page_chooser_viewset,
)
from cms.topics.viewsets.series_with_headline_figures import series_with_headline_figures_chooser_viewset


class FeaturedSeriesPageChooserViewSetTest(WagtailTestUtils, TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.superuser = cls.create_superuser(username="admin")
        # Create test pages
        cls.topic_page = TopicPageFactory(title="PSF")
        cls.series1 = ArticleSeriesPageFactory(parent=cls.topic_page, title="Series A")
        cls.series2 = ArticleSeriesPageFactory(parent=cls.topic_page, title="Series B")

        cls.another_topic = TopicPageFactory(title="GDP")
        cls.another_series = ArticleSeriesPageFactory(parent=cls.another_topic, title="Series Z")

        cls.chooser_url = featured_series_page_chooser_viewset.widget_class().get_chooser_modal_url()
        cls.chooser_results_url = reverse(featured_series_page_chooser_viewset.get_url_name("choose_results"))

        cls.unused_topic = TopicPageFactory(title="CPI")

    def setUp(self):
        self.client.force_login(self.superuser)

    def test_choose_view(self):
        """Test the choose view loads with the expected content."""
        response = self.client.get(self.chooser_url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "wagtailadmin/generic/chooser/chooser.html")

        for title in [self.series1.title, self.series2.title, self.another_series.title]:
            self.assertContains(response, title)

        self.assertContains(response, self.topic_page.title)
        self.assertContains(response, self.another_topic.title)
        self.assertNotContains(response, self.unused_topic.title)

        # Check column headers
        self.assertContains(response, "Topic")
        self.assertContains(response, "Updated")
        self.assertContains(response, "Status")
        self.assertContains(response, "Locale")

    def test_chooser_search(self):
        """Test the AJAX results view."""
        rebuild_internal_search_index()
        response = self.client.get(f"{self.chooser_results_url}?q=Series A")

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "wagtailadmin/generic/chooser/results.html")

        self.assertContains(response, self.topic_page.title)
        self.assertContains(response, self.series1.title)
        self.assertNotContains(response, self.series2.title)
        self.assertNotContains(response, self.another_series.title)
        self.assertNotContains(response, self.another_topic.title)

    def test_featured_series_viewset_configuration(self):
        self.assertFalse(featured_series_page_chooser_viewset.register_widget)
        self.assertEqual(featured_series_page_chooser_viewset.model, ArticleSeriesPageFactory._meta.model)
        self.assertEqual(featured_series_page_chooser_viewset.choose_one_text, "Choose Article Series page")
        self.assertEqual(featured_series_page_chooser_viewset.choose_another_text, "Choose another Article Series page")
        self.assertEqual(featured_series_page_chooser_viewset.edit_item_text, "Edit Article Series page")


class HighlightedPageChooserViewSetTest(WagtailTestUtils, TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.superuser = cls.create_superuser(username="admin")

        # Create test pages
        cls.topic_page = TopicPageFactory()
        cls.article_series = ArticleSeriesPageFactory(parent=cls.topic_page)
        cls.article = StatisticalArticlePageFactory(
            parent=cls.article_series,
            title="Article 1",
            release_date=datetime(2024, 1, 1),
        )
        cls.second_article = StatisticalArticlePageFactory(
            parent=cls.article_series,
            title="Another Article",
            release_date=datetime(2024, 2, 1),
        )

        cls.another_article = StatisticalArticlePageFactory(title="Article in another topic")
        cls.methodology = MethodologyPageFactory(
            parent=cls.topic_page,
            title="Methodology 1",
            publication_date=datetime(2024, 1, 1),
        )
        cls.second_methodology = MethodologyPageFactory(
            parent=cls.topic_page,
            title="Another Methodology",
            publication_date=datetime(2023, 1, 1),
        )

        cls.unused_methodology = MethodologyPageFactory(
            title="Unused Method",
            publication_date=datetime(2024, 1, 1),
        )

        cls.article_chooser_url = highlighted_article_page_chooser_viewset.widget_class().get_chooser_modal_url()
        cls.article_chooser_results_url = reverse(
            highlighted_article_page_chooser_viewset.get_url_name("choose_results")
        )
        cls.methodology_chooser_url = (
            highlighted_methodology_page_chooser_viewset.widget_class().get_chooser_modal_url()
        )
        cls.methodology_chooser_results_url = reverse(
            highlighted_methodology_page_chooser_viewset.get_url_name("choose_results")
        )

        rebuild_internal_search_index()

    def setUp(self):
        self.client.force_login(self.superuser)

    def test_article_choose_view_with_topic_filter(self):
        """Test the article chooser view with topic_page_id filter."""
        response = self.client.get(f"{self.article_chooser_url}?topic_page_id={self.topic_page.id}")

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "wagtailadmin/generic/chooser/chooser.html")

        # Check articles are shown
        self.assertListEqual(
            response.context["items"].object_list,
            [self.second_article, self.article],
        )

        # Check column headers
        self.assertContains(response, "Release date")
        self.assertContains(response, "Status")

    def test_article_choose_view_without_topic_filter(self):
        """Test the article chooser view without topic_page_id returns no results."""
        response = self.client.get(self.article_chooser_url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "wagtailadmin/generic/chooser/chooser.html")
        self.assertNotContains(response, "Article 1")
        self.assertNotContains(response, "Article 2")

    def test_article_choose_view_columns(self):
        response = self.client.get(f"{self.article_chooser_url}?topic_page_id={self.topic_page.id}")

        self.assertEqual(response.status_code, 200)

        # Check column headers
        self.assertContains(response, "Release date")
        self.assertContains(response, "Status")
        self.assertContains(response, "Locale")

        # Check values
        self.assertContains(response, "1 January 2024")
        self.assertContains(response, "English")
        self.assertContains(response, "live")

    def test_article_results_view_with_topic_filter(self):
        """Test the article AJAX results view with topic_page_id filter."""
        response = self.client.get(f"{self.article_chooser_results_url}?topic_page_id={self.topic_page.id}&q=Another")

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "wagtailadmin/generic/chooser/results.html")

        # Check articles are ordered by release_date descending
        self.assertListEqual(
            response.context["items"].object_list,
            [self.second_article],
        )

    def test_methodology_choose_view_with_topic_filter(self):
        """Test the methodology chooser view with topic_page_id filter."""
        response = self.client.get(f"{self.methodology_chooser_url}?topic_page_id={self.topic_page.id}")

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "wagtailadmin/generic/chooser/chooser.html")

        # Check methodology is shown
        self.assertListEqual(
            response.context["items"].object_list,
            [self.methodology, self.second_methodology],
        )

    def test_methodology_results_view_with_topic_filter(self):
        """Test the methodology AJAX results view with topic_page_id filter."""
        response = self.client.get(
            f"{self.methodology_chooser_results_url}?topic_page_id={self.topic_page.id}&q=Another"
        )

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "wagtailadmin/generic/chooser/results.html")

        self.assertListEqual(
            response.context["items"].object_list,
            [self.second_methodology],
        )

    def test_highlighted_article_viewset_configuration(self):
        self.assertFalse(highlighted_article_page_chooser_viewset.register_widget)
        self.assertEqual(highlighted_article_page_chooser_viewset.model, StatisticalArticlePageFactory._meta.model)
        self.assertEqual(highlighted_article_page_chooser_viewset.choose_one_text, "Choose Article page")
        self.assertEqual(highlighted_article_page_chooser_viewset.choose_another_text, "Choose another Article page")
        self.assertEqual(highlighted_article_page_chooser_viewset.edit_item_text, "Edit Article page")
        self.assertIn("topic_page_id", highlighted_article_page_chooser_viewset.preserve_url_parameters)

    def test_highlighted_methodology_viewset_configuration(self):
        self.assertFalse(highlighted_methodology_page_chooser_viewset.register_widget)
        self.assertEqual(highlighted_methodology_page_chooser_viewset.model, MethodologyPageFactory._meta.model)
        self.assertEqual(highlighted_methodology_page_chooser_viewset.choose_one_text, "Choose Methodology page")
        self.assertEqual(
            highlighted_methodology_page_chooser_viewset.choose_another_text, "Choose another Methodology page"
        )
        self.assertEqual(highlighted_methodology_page_chooser_viewset.edit_item_text, "Edit Methodology page")
        self.assertIn("topic_page_id", highlighted_methodology_page_chooser_viewset.preserve_url_parameters)


class SeriesWithHeadlineFiguresChooserViewSetTest(WagtailTestUtils, TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.superuser = cls.create_superuser(username="admin")

        # Create test pages
        cls.topic_page = TopicPageFactory(title="PSF")
        cls.series1 = ArticleSeriesPageFactory(parent=cls.topic_page, title="Series A")
        cls.series2 = ArticleSeriesPageFactory(parent=cls.topic_page, title="Series B")

        cls.series1_article = StatisticalArticlePageFactory(
            parent=cls.series1,
            title="Article 1",
            release_date=datetime(2024, 1, 1),
            headline_figures=[
                {
                    "type": "figure",
                    "value": {
                        "figure_id": "figurexyz",
                        "title": "Foobar figure title",
                        "figure": "999 million",
                        "supporting_text": "Figure supporting text XYZ",
                    },
                },
                {
                    "type": "figure",
                    "value": {
                        "figure_id": "figureabc",
                        "title": "Lorem ipsum figure title",
                        "figure": "123 billion",
                        "supporting_text": "Figure supporting text ABC",
                    },
                },
            ],
            headline_figures_figure_ids="figurexyz,figureabc",
        )
        cls.series2_article = StatisticalArticlePageFactory(
            parent=cls.series2,
            title="Article 2",
            release_date=datetime(2024, 2, 1),
            headline_figures=[
                {
                    "type": "figure",
                    "value": {
                        "figure_id": "foobar123",
                        "title": "Another figure title for completeness",
                        "figure": "100 Billion and many more",
                        "supporting_text": "Figure supporting text 123",
                    },
                },
                {
                    "type": "figure",
                    "value": {
                        "figure_id": "foobar321",
                        "title": "John Doe figure title",
                        "figure": "100 Billion and many more",
                        "supporting_text": "Figure supporting text 321",
                    },
                },
            ],
            headline_figures_figure_ids="foobar123,foobar321",
        )

        cls.chooser_url = series_with_headline_figures_chooser_viewset.widget_class().get_chooser_modal_url()
        cls.chooser_results_url = reverse(series_with_headline_figures_chooser_viewset.get_url_name("choose_results"))

    def setUp(self):
        self.client.force_login(self.superuser)

    def test_choose_view_with_topic_filter(self):
        """Test the article chooser view with topic_page_id filter."""
        response = self.client.get(f"{self.chooser_url}?topic_page_id={self.topic_page.id}")

        self.assertEqual(response.status_code, 200)

        self.assertTemplateUsed(response, "wagtailadmin/generic/chooser/chooser.html")

        self.assertContains(response, "Foobar figure title")
        self.assertContains(response, "999 million")
        self.assertContains(response, "Figure supporting text XYZ")
        self.assertContains(response, "Lorem ipsum figure title")
        self.assertContains(response, "123 billion")
        self.assertContains(response, "Figure supporting text ABC")
        self.assertContains(response, "Another figure title for completeness")
        self.assertContains(response, "John Doe figure title")
        self.assertContains(response, "Figure supporting text 123")
        self.assertContains(response, "Figure supporting text 321")

        self.assertContains(response, "PSF")
        self.assertContains(response, "Series A")
        self.assertContains(response, "Series B")

    def test_choose_view_displays_latest_figures_only(self):
        """Test the article chooser view with topic_page_id filter."""
        StatisticalArticlePageFactory(
            parent=self.series1,
            title="Newer Article",
            headline_figures=[
                {
                    "type": "figure",
                    "value": {
                        "figure_id": "new_figure",
                        "title": "New figure title",
                        "figure": "1234 billion",
                        "supporting_text": "Figure supporting text ABC",
                    },
                },
                {
                    "type": "figure",
                    "value": {
                        "figure_id": "new_figure_2",
                        "title": "Another new figure title",
                        "figure": "2999 quadrillion",
                        "supporting_text": "Figure supporting text ABC",
                    },
                },
            ],
            headline_figures_figure_ids="new_figure,new_figure_2",
        )

        response = self.client.get(f"{self.chooser_url}?topic_page_id={self.topic_page.id}")

        self.assertEqual(response.status_code, 200)

        # Check series are shown
        self.assertNotContains(response, "Foobar figure title")
        self.assertNotContains(response, "Lorem ipsum figure title")
        self.assertNotContains(response, "999 million")

        self.assertContains(response, "New figure title")
        self.assertContains(response, "Another new figure title")
        self.assertContains(response, "1234 billion")
        self.assertContains(response, "John Doe figure title")
        self.assertContains(response, "2999 quadrillion")
        self.assertContains(response, "Another figure title for completeness")
        self.assertContains(response, "Figure supporting text 123")

    def test_choose_view_updated_value(self):
        """Test the article chooser view with topic_page_id filter."""
        self.series1_article.latest_revision_created_at = datetime(2024, 1, 1, tzinfo=timezone.get_default_timezone())
        self.series1_article.save()

        self.series2_article.latest_revision_created_at = datetime(2025, 2, 1, tzinfo=timezone.get_default_timezone())
        self.series2_article.save()

        response = self.client.get(f"{self.chooser_url}?topic_page_id={self.topic_page.id}")

        self.assertEqual(response.status_code, 200)

        self.assertContains(response, "1 January 2024")
        self.assertContains(response, "1 February 2025")

    def test_choose_view_logs_viewed_headline_figures(self):
        """Test that viewing headline figures in the chooser creates an audit log entry."""
        with patch("cms.core.audit.audit_logger") as mock_logger:
            self.client.get(f"{self.chooser_url}?topic_page_id={self.topic_page.id}")

            mock_logger.info.assert_called_once()
            call_args = mock_logger.info.call_args
            extra = call_args[1]["extra"]

            self.assertEqual(extra["event"], "topics.headline_figures_chooser.view")
            self.assertEqual(extra["object_id"], self.topic_page.id)
            self.assertIn("figurexyz", extra["data"]["figure_ids"])
            self.assertIn("figureabc", extra["data"]["figure_ids"])
            self.assertIn("foobar123", extra["data"]["figure_ids"])
            self.assertIn("foobar321", extra["data"]["figure_ids"])

    def test_choose_view_creates_page_log_entry(self):
        """Test that viewing headline figures creates a PageLogEntry for the topic page."""
        initial_count = PageLogEntry.objects.filter(
            page=self.topic_page,
            action="topics.headline_figures_chooser.view",
        ).count()

        self.client.get(f"{self.chooser_url}?topic_page_id={self.topic_page.id}")

        log_entries = PageLogEntry.objects.filter(
            page=self.topic_page,
            action="topics.headline_figures_chooser.view",
        )
        self.assertEqual(log_entries.count(), initial_count + 1)

        log_entry = log_entries.latest("timestamp")
        self.assertEqual(log_entry.user, self.superuser)
        self.assertIn("figurexyz", log_entry.data["figure_ids"])
        self.assertIn("figureabc", log_entry.data["figure_ids"])

    def test_choose_view_does_not_log_without_topic_page_id(self):
        """Test that no audit log is created when topic_page_id is not provided."""
        initial_count = PageLogEntry.objects.filter(
            action="topics.headline_figures_chooser.view",
        ).count()

        self.client.get(self.chooser_url)

        self.assertEqual(
            PageLogEntry.objects.filter(action="topics.headline_figures_chooser.view").count(),
            initial_count,
        )

    def test_choose_view_does_not_log_for_invalid_topic_page_id(self):
        """Test that no audit log is created when topic_page_id is invalid."""
        initial_count = PageLogEntry.objects.filter(
            action="topics.headline_figures_chooser.view",
        ).count()

        self.client.get(f"{self.chooser_url}?topic_page_id=99999")

        self.assertEqual(
            PageLogEntry.objects.filter(action="topics.headline_figures_chooser.view").count(),
            initial_count,
        )

    def test_results_view_logs_viewed_headline_figures(self):
        """Test that the results view also logs viewed headline figures."""
        with patch("cms.core.audit.audit_logger") as mock_logger:
            self.client.get(f"{self.chooser_results_url}?topic_page_id={self.topic_page.id}")

            mock_logger.info.assert_called_once()
            call_args = mock_logger.info.call_args
            extra = call_args[1]["extra"]

            self.assertEqual(extra["event"], "topics.headline_figures_chooser.view")
            self.assertEqual(extra["object_id"], self.topic_page.id)

    def test_log_entry_contains_only_figure_ids(self):
        """Test that the log entry only contains figure IDs, not sensitive figure data."""
        # Sanity check - ensure no log entries exist before the test
        self.assertFalse(
            PageLogEntry.objects.filter(
                action="topics.headline_figures_chooser.view",
            ).exists()
        )

        self.client.get(f"{self.chooser_url}?topic_page_id={self.topic_page.id}")

        log_entry = PageLogEntry.objects.filter(
            page=self.topic_page,
            action="topics.headline_figures_chooser.view",
        ).latest("timestamp")

        # Verify only figure_ids key is present in data
        self.assertEqual(list(log_entry.data.keys()), ["figure_ids"])

        # Verify figure values/text are not logged
        data_str = str(log_entry.data)

        self.assertNotIn("999 million", data_str)
        self.assertNotIn("123 billion", data_str)
        self.assertNotIn("Foobar figure title", data_str)
        self.assertNotIn("Figure supporting text", data_str)
        self.assertIn("figurexyz", data_str)
        self.assertIn("figureabc", data_str)
