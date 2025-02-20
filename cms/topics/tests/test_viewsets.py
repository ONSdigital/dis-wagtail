from datetime import datetime

from django.test import TestCase
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from wagtail.test.utils import WagtailTestUtils

from cms.articles.tests.factories import ArticleSeriesPageFactory, StatisticalArticlePageFactory
from cms.methodology.tests.factories import MethodologyPageFactory
from cms.topics.tests.factories import TopicPageFactory
from cms.topics.viewsets import (
    featured_series_page_chooser_viewset,
    highlighted_article_page_chooser_viewset,
    highlighted_methodology_page_chooser_viewset,
)


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

    def test_chooser_search(self):
        """Test the AJAX results view."""
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
        self.assertEqual(featured_series_page_chooser_viewset.choose_one_text, _("Choose Article Series page"))
        self.assertEqual(
            featured_series_page_chooser_viewset.choose_another_text, _("Choose another Article Series page")
        )
        self.assertEqual(featured_series_page_chooser_viewset.edit_item_text, _("Edit Article Series page"))


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
        self.assertEqual(highlighted_article_page_chooser_viewset.choose_one_text, _("Choose Article page"))
        self.assertEqual(highlighted_article_page_chooser_viewset.choose_another_text, _("Choose another Article page"))
        self.assertEqual(highlighted_article_page_chooser_viewset.edit_item_text, _("Edit Article page"))
        self.assertIn("topic_page_id", highlighted_article_page_chooser_viewset.preserve_url_parameters)

    def test_highlighted_methodology_viewset_configuration(self):
        self.assertFalse(highlighted_methodology_page_chooser_viewset.register_widget)
        self.assertEqual(highlighted_methodology_page_chooser_viewset.model, MethodologyPageFactory._meta.model)
        self.assertEqual(highlighted_methodology_page_chooser_viewset.choose_one_text, _("Choose Methodology page"))
        self.assertEqual(
            highlighted_methodology_page_chooser_viewset.choose_another_text, _("Choose another Methodology page")
        )
        self.assertEqual(highlighted_methodology_page_chooser_viewset.edit_item_text, _("Edit Methodology page"))
        self.assertIn("topic_page_id", highlighted_methodology_page_chooser_viewset.preserve_url_parameters)
