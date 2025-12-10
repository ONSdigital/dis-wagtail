from http import HTTPStatus

from django.urls import reverse
from wagtail.blocks import StreamValue
from wagtail.test.utils import WagtailPageTestCase

from cms.articles.tests.factories import ArticleSeriesPageFactory, StatisticalArticlePageFactory
from cms.datasets.blocks import DatasetStoryBlock
from cms.datasets.models import Dataset
from cms.topics.blocks import TimeSeriesPageStoryBlock
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

    def test_topic_page_displays_datasets(self):
        lookup_dataset = Dataset.objects.create(
            namespace="LOOKUP",
            edition="lookup_edition",
            version=1,
            title="test lookup",
            description="lookup description",
        )
        manual_dataset = {"title": "test manual", "description": "manual description", "url": "https://example.com"}

        self.page.datasets = StreamValue(
            DatasetStoryBlock(),
            stream_data=[
                ("dataset_lookup", lookup_dataset),
                ("manual_link", manual_dataset),
            ],
        )
        self.page.save_revision().publish()

        response = self.client.get(self.page.url)

        self.assertContains(response, "<h2>Data</h2>")
        self.assertContains(response, '<section id="data"')

        self.assertContains(response, lookup_dataset.title)
        self.assertContains(response, lookup_dataset.description)
        self.assertContains(response, lookup_dataset.url_path)

        self.assertContains(response, manual_dataset["title"])
        self.assertContains(response, manual_dataset["description"])
        self.assertContains(response, manual_dataset["url"])

        self.assertIn(
            {
                "url": "#data",
                "text": "Data",
                "attributes": {
                    "data-ga-event": "navigation-onpage",
                    "data-ga-navigation-type": "table-of-contents",
                    "data-ga-section-title": "Data",
                },
            },
            self.page.table_of_contents,
        )

    def test_topic_page_displays_time_series(self):
        title = "Test Time Series"
        url = "https://example.com/dataset"
        description = "This is a Time Series page summary."

        self.page.time_series = StreamValue(
            TimeSeriesPageStoryBlock(),
            stream_data=[("time_series_page_link", {"title": title, "url": url, "description": description})],
        )
        self.page.save_revision().publish()

        response = self.client.get(self.page.url)

        self.assertContains(response, "<h2>Time Series</h2>")
        self.assertContains(response, '<section id="time-series"')

        self.assertContains(response, title)
        self.assertContains(response, url)
        self.assertContains(response, description)

        self.assertIn(
            {
                "url": "#time-series",
                "text": "Time series",
                "attributes": {
                    "data-ga-event": "navigation-onpage",
                    "data-ga-navigation-type": "table-of-contents",
                    "data-ga-section-title": "Time series",
                },
            },
            self.page.table_of_contents,
        )

    def test_topic_page_displays_with_broken_headline_figures(self):
        """Test that the topic page renders correctly even when it contains a broken headline figure reference."""
        self.page.headline_figures.extend(
            [
                (
                    "figure",
                    {
                        "series": self.series,
                        "figure_id": "broken1",
                    },
                ),
                (
                    "figure",
                    {
                        "series": self.series,
                        "figure_id": "broken2",
                    },
                ),
            ]
        )
        self.page.save_revision().publish()

        response = self.client.get(self.page.url)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertContains(response, self.page.title)
        self.assertContains(response, "Error retrieving figure")
