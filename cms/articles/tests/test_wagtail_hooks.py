from django.test import TestCase
from django.urls import reverse
from wagtail.test.utils import WagtailTestUtils
from wagtail.test.utils.form_data import nested_form_data

from cms.articles.tests.factories import ArticleSeriesPageFactory, StatisticalArticlePageFactory
from cms.topics.tests.factories import TopicPageFactory


class ArticleHeadlineFiguresHooksTestCase(WagtailTestUtils, TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.topic_page = TopicPageFactory()
        cls.series_page = ArticleSeriesPageFactory(parent=cls.topic_page)
        cls.article_page = StatisticalArticlePageFactory(parent=cls.series_page)

    def setUp(self):
        self.login()

    def test_user_cannot_delete_article_with_referenced_figures(self):
        # Given
        self.add_headline_figures_to_article_and_topic_pages()
        data = nested_form_data({})

        # When
        response = self.client.post(
            reverse("wagtailadmin_pages:delete", args=(self.article_page.id,)), data, follow=True
        )

        # Then
        # The response should be a redirect back to the delete confirmation page with a warning message
        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response, "This page cannot be deleted because it contains headline figures that are referenced elsewhere."
        )

        # Verify the page still exists, delete was prevented
        self.article_page.refresh_from_db()

    def test_user_cannot_unpublish_article_with_referenced_figures(self):
        # Given
        self.add_headline_figures_to_article_and_topic_pages()
        data = nested_form_data({})

        # When
        response = self.client.post(
            reverse("wagtailadmin_pages:unpublish", args=(self.article_page.id,)), data, follow=True
        )

        # Then
        # The response should be a redirect back to the unpublish confirmation page with a warning message
        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            "This page cannot be unpublished because it contains headline figures that are referenced elsewhere.",
        )

        # Verify the page is still live, unpublish was prevented
        self.article_page.refresh_from_db()
        self.assertTrue(self.article_page.live)

    def add_headline_figures_to_article_and_topic_pages(self) -> None:
        """Add headline figures to the test article page, and reference them from the topic page."""
        figure_ids = ["figure1", "figure2"]
        self.article_page.headline_figures = [
            {
                "type": "figure",
                "value": {
                    "figure_id": figure_ids[0],
                    "title": "Test Figure 1",
                    "figure": "1",
                    "supporting_text": "Figure supporting text 1",
                },
            },
            {
                "type": "figure",
                "value": {
                    "figure_id": figure_ids[1],
                    "title": "Test Figure 2",
                    "figure": "2",
                    "supporting_text": "Figure supporting text 2",
                },
            },
        ]
        self.article_page.update_headline_figures_figure_ids(figure_ids)
        self.article_page.save_revision().publish()
        self.topic_page.headline_figures = [
            (
                "figure",
                {
                    "series": self.series_page,
                    "figure_id": figure_ids[0],
                },
            ),
            (
                "figure",
                {
                    "series": self.series_page,
                    "figure_id": figure_ids[1],
                },
            ),
        ]
        self.topic_page.save_revision().publish()
