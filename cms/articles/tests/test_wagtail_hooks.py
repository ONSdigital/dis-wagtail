from datetime import timedelta

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

        cls.figure_ids = ("figure1", "figure2")
        cls.article_page.headline_figures = [
            {
                "type": "figure",
                "value": {
                    "figure_id": cls.figure_ids[0],
                    "title": "Test Figure 1",
                    "figure": "1",
                    "supporting_text": "Figure supporting text 1",
                },
            },
            {
                "type": "figure",
                "value": {
                    "figure_id": cls.figure_ids[1],
                    "title": "Test Figure 2",
                    "figure": "2",
                    "supporting_text": "Figure supporting text 2",
                },
            },
        ]
        cls.article_page.update_headline_figures_figure_ids(cls.figure_ids)
        cls.article_page.save_revision().publish()
        cls.topic_page.headline_figures = [
            (
                "figure",
                {
                    "series": cls.series_page,
                    "figure_id": cls.figure_ids[0],
                },
            ),
            (
                "figure",
                {
                    "series": cls.series_page,
                    "figure_id": cls.figure_ids[1],
                },
            ),
        ]
        cls.topic_page.save_revision().publish()

    def setUp(self):
        self.login()

    def test_user_cannot_delete_article_with_referenced_figures(self):
        # When
        data = nested_form_data({})
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

    def test_user_cannot_unpublish_lone_article_in_series_with_referenced_figures(self):
        # When
        data = nested_form_data({})
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

    def test_user_cannot_unpublish_article_with_referenced_figures_with_no_fallbacks(self):
        # Given
        # Add an older article in the series without the headline figures
        older_article_page = StatisticalArticlePageFactory(parent=self.series_page)
        older_article_page.release_date = self.article_page.release_date - timedelta(days=1)
        older_article_page.next_release_date = older_article_page.release_date + timedelta(days=1)
        older_article_page.save_revision().publish()

        # When
        data = nested_form_data({})
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

    def test_user_can_unpublish_article_with_figures_when_there_are_fallbacks(self):
        """Test that unpublishing an article with referenced figures is allowed if the previous article in the series
        also has the referenced figures, so nothing will break.
        """
        # Given
        # Add a new latest article in the series with the same headline figures, which should be unpublishable safely
        new_article_page = StatisticalArticlePageFactory(parent=self.series_page)
        new_article_page.headline_figures = self.article_page.headline_figures
        new_article_page.update_headline_figures_figure_ids(self.figure_ids)
        new_article_page.release_date = self.article_page.release_date + timedelta(days=1)
        new_article_page.next_release_date = new_article_page.release_date + timedelta(days=1)
        new_article_page.save_revision().publish()

        # When
        data = nested_form_data({})
        response = self.client.post(
            reverse("wagtailadmin_pages:unpublish", args=(new_article_page.id,)), data, follow=True
        )

        # Then
        self.assertEqual(response.status_code, 200)

        # Verify the page now unpublished/not live
        new_article_page.refresh_from_db()
        self.assertFalse(new_article_page.live)

    def test_user_can_unpublish_article_with_figures_when_it_is_not_latest(self):
        """Test that unpublishing an article with referenced figures is allowed when the article is not the latest in
        the series.
        """
        # Given
        # Add an older article in the series with the same headline figures, which should be unpublishable safely
        older_article_page = StatisticalArticlePageFactory(parent=self.series_page)
        older_article_page.headline_figures = self.article_page.headline_figures
        older_article_page.update_headline_figures_figure_ids(self.figure_ids)
        older_article_page.release_date = self.article_page.release_date - timedelta(days=1)
        older_article_page.next_release_date = older_article_page.release_date + timedelta(days=1)
        older_article_page.save_revision().publish()

        data = nested_form_data({})

        # When
        response = self.client.post(
            reverse("wagtailadmin_pages:unpublish", args=(older_article_page.id,)), data, follow=True
        )

        # Then
        self.assertEqual(response.status_code, 200)

        # Verify the page now unpublished/not live
        older_article_page.refresh_from_db()
        self.assertFalse(older_article_page.live)
