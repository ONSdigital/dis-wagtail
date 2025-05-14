from http import HTTPStatus

from django.urls import reverse
from wagtail.test.utils import WagtailPageTestCase

from cms.articles.tests.factories import ArticleSeriesPageFactory, StatisticalArticlePageFactory
from cms.topics.tests.factories import TopicPageFactory


class TopicPageTests(WagtailPageTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.page = TopicPageFactory()
        cls.series = ArticleSeriesPageFactory(parent=cls.page)
        cls.superuser = cls.create_superuser(username="admin")

        cls.statistical_article_page = StatisticalArticlePageFactory(parent=cls.series)
        cls.statistical_article_page.headline_figures = [
            {
                "type": "figure",
                "value": {
                    "figure_id": "figurexyz",
                    "title": "Figure title XYZ",
                    "figure": "XYZ",
                    "supporting_text": "Figure supporting text XYZ",
                },
            },
            {
                "type": "figure",
                "value": {
                    "figure_id": "figureabc",
                    "title": "Figure title ABC",
                    "figure": "ABC",
                    "supporting_text": "Figure supporting text ABC",
                },
            },
        ]
        cls.statistical_article_page.headline_figures_figure_ids = "figurexyz,figureabc"
        cls.statistical_article_page.save_revision().publish()

    def test_default_route(self):
        self.assertPageIsRoutable(self.page)

    def test_default_route_is_renderable(self):
        self.assertPageIsRenderable(self.page)

    def test_default_route_rendering(self):
        response = self.client.get(self.page.url)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertContains(response, self.page.title)

        self.assertContains(response, "Contents")
        self.assertContains(response, "Sections in this page")

    def test_topic_page_displays_headline_figures(self):
        self.page.headline_figures.extend(
            [
                (
                    "figure",
                    {
                        "series": self.series,
                        "figure_id": "figurexyz",
                    },
                ),
                (
                    "figure",
                    {
                        "series": self.series,
                        "figure_id": "figureabc",
                    },
                ),
            ]
        )
        self.page.save_revision().publish()

        response = self.client.get(self.page.url)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertContains(response, "Figure title XYZ")
        self.assertContains(response, "Figure supporting text XYZ")
        self.assertContains(response, "Figure title ABC")
        self.assertContains(response, "Figure supporting text ABC")

        # When the statistical article updates the figures, the topic page should reflect the changes.
        self.statistical_article_page.headline_figures = [
            {
                "type": "figure",
                "value": {
                    "figure_id": "figurexyz",
                    "title": "New figure title updated XYZ",
                    "figure": "XYZ",
                    "supporting_text": "Figure supporting text XYZ",
                },
            },
            {
                "type": "figure",
                "value": {
                    "figure_id": "figureabc",
                    "title": "New figure title updated ABC",
                    "figure": "ABC",
                    "supporting_text": "Figure supporting text ABC",
                },
            },
        ]

        self.statistical_article_page.save_revision().publish()

        # Re-fetch the page to ensure the changes are reflected.
        response = self.client.get(self.page.url)
        self.assertContains(response, "New figure title updated XYZ")
        self.assertContains(response, "New figure title updated ABC")

    def test_copy_is_not_allowed(self):
        """Test that copying a TopicPage raises a warning."""
        self.client.force_login(self.superuser)
        response = self.client.get(
            reverse("wagtailadmin_pages:copy", args=[self.page.id]),
        )
        self.assertEqual(response.status_code, HTTPStatus.FOUND)
        response = self.client.get(
            reverse("wagtailadmin_pages:copy", args=[self.page.id]),
            follow=True,
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertContains(
            response,
            "Topic and theme pages cannot be duplicated as selected taxonomy needs to be unique for each page.",
        )

        response = self.client.post(
            reverse("wagtailadmin_pages:copy", args=[self.page.id]),
        )
        self.assertEqual(response.status_code, HTTPStatus.FOUND)
        response = self.client.post(
            reverse("wagtailadmin_pages:copy", args=[self.page.id]),
            follow=True,
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertContains(
            response,
            "Topic and theme pages cannot be duplicated as selected taxonomy needs to be unique for each page.",
        )
