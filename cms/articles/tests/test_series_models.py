from http import HTTPStatus

from django.test import RequestFactory, TestCase, override_settings
from django.utils import timezone
from wagtail.blocks import StreamValue
from wagtail.models import Locale
from wagtail.test.utils import WagtailTestUtils

from cms.articles.tests.factories import ArticleSeriesPageFactory, StatisticalArticlePageFactory
from cms.datasets.blocks import DatasetStoryBlock


class ArticleSeriesTestCase(WagtailTestUtils, TestCase):
    """Test ArticleSeriesPage model methods."""

    @classmethod
    def setUpTestData(cls):
        cls.series = ArticleSeriesPageFactory()

    def test_index_redirect_404_with_no_subpages(self):
        """Test index path redirects to latest."""
        response = self.client.get(self.series.url)
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    def test_get_latest_no_subpages(self):
        """Test get_latest returns None when no pages exist."""
        self.assertIsNone(self.series.get_latest())

    def test_get_latest_with_subpages(self):
        StatisticalArticlePageFactory(parent=self.series, release_date=timezone.now().date())
        latest_page = StatisticalArticlePageFactory(
            parent=self.series,
            release_date=timezone.now().date() + timezone.timedelta(days=1),
        )

        self.assertEqual(self.series.get_latest(), latest_page)

    def test_latest_release_404(self):
        """Test latest_release returns 404 when no pages exist."""
        response = self.client.get(self.series.url)
        self.assertEqual(response.status_code, 404)

    def test_latest_release_success(self):
        """Test latest_release returns the latest page."""
        article_page = StatisticalArticlePageFactory(parent=self.series)
        series_response = self.client.get(self.series.url)
        self.assertEqual(series_response.status_code, 200)

        article_page_response = self.client.get(article_page.url)
        self.assertEqual(article_page_response.status_code, 200)

        self.assertEqual(series_response.context, article_page_response.context)

    def test_latest_release_external_env(self):
        """Test latest_release in external env."""
        StatisticalArticlePageFactory(parent=self.series)

        with override_settings(IS_EXTERNAL_ENV=True):
            series_response = self.client.get(self.series.url)

        self.assertEqual(series_response.status_code, 200)


class ArticleSeriesEvergreenUrlTestCase(WagtailTestUtils, TestCase):
    def setUp(self):
        self.article_series_page = ArticleSeriesPageFactory()
        self.article_with_datasets = StatisticalArticlePageFactory(parent=self.article_series_page)
        self.article_with_datasets.datasets = StreamValue(
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
        self.article_with_datasets.save_revision().publish()

    def test_evergreen_route_links_to_evergreen_related_data(self):
        """Test that the evergreen page links to the evergreen related data page."""
        response = self.client.get(self.article_series_page.url, follow=True)
        self.assertEqual(response.status_code, HTTPStatus.OK)

        self.assertContains(
            response,
            f'<a href="{self.article_series_page.get_relative_path()}/related-data" class="ons-list__link">'
            + "View data used in this article</a>",
            html=True,
        )

    def test_evergreen_route_related_data_renders_correctly(self):
        """Check that the expected content is rendered on the evergreen related data page."""
        response = self.client.get(f"{self.article_series_page.url}/related-data")
        self.assertEqual(response.status_code, HTTPStatus.OK)

        self.assertContains(response, f"All data related to {self.article_with_datasets.title}")
        self.assertContains(response, "Test dataset")

    def test_evergreen_route_related_data_canonical_url(self):
        """Test that the canonical URL on the related data page is the evergreen series URL."""
        response = self.client.get(f"{self.article_series_page.url}/related-data")
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertContains(
            response, f'<link rel="canonical" href="{self.article_series_page.get_full_url()}/related-data">', html=True
        )

    def test_evergreen_route_related_data_latest_article_canonical_url(self):
        """Test that latest article's related data page has evergreen canonical URL."""
        # article_with_datasets is the latest article in setUp
        response = self.client.get(f"{self.article_with_datasets.url}/related-data")
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertContains(
            response, f'<link rel="canonical" href="{self.article_series_page.get_full_url()}/related-data">', html=True
        )

    def test_evergreen_route_related_data_non_latest_article_canonical_url(self):
        """Test that non-latest article's related data page has its own canonical URL."""
        # Create newer article to make the existing one non-latest
        newer_article = StatisticalArticlePageFactory(
            parent=self.article_series_page,
            release_date=self.article_with_datasets.release_date + timezone.timedelta(days=1),
        )
        newer_article.datasets = StreamValue(
            DatasetStoryBlock(),
            stream_data=[
                (
                    "manual_link",
                    {
                        "title": "Newer dataset",
                        "description": "Newer description",
                        "url": "https://example.com/newer",
                    },
                )
            ],
        )
        newer_article.save_revision().publish()

        self.assertFalse(self.article_with_datasets.is_latest)

        response = self.client.get(f"{self.article_with_datasets.url}/related-data")
        self.assertEqual(response.status_code, HTTPStatus.OK)

        # The RequestFactory's default SERVER_NAME is 'testserver'.
        # This is what is used in the request when building canonical URLs for this specific page.
        request_factory = RequestFactory()
        request_factory_server_name = request_factory._base_environ()["SERVER_NAME"]  # pylint: disable=protected-access

        self.assertContains(
            response,
            f'<link rel="canonical" href="http://{request_factory_server_name}{
                self.article_with_datasets.get_relative_path()
            }/related-data">',
            html=True,
        )
        self.assertNotContains(
            response,
            f'<link rel="canonical" href="http://{request_factory_server_name}{
                self.article_series_page.url
            }/related-data">',
            html=True,
        )

    def test_evergreen_route_related_data_returns_404_when_no_live_editions(self):
        series_with_no_editions = ArticleSeriesPageFactory()
        response = self.client.get(f"{series_with_no_editions.url}/related-data")
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    def test_evergreen_route_related_data_returns_404_when_no_datasets(self):
        latest_article_without_datasets = StatisticalArticlePageFactory(
            parent=self.article_series_page,
            release_date=self.article_with_datasets.release_date + timezone.timedelta(days=1),
        )

        self.assertTrue(latest_article_without_datasets.is_latest)

        response = self.client.get(f"{self.article_series_page.url}/related-data")
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    def test_evergreen_route_related_data_welsh_alias_canonical_url(self):
        """Test that Welsh alias article's related data page has English canonical URL."""
        welsh_article_alias = self.article_with_datasets.copy_for_translation(
            locale=Locale.objects.get(language_code="cy"), copy_parents=True, alias=True
        )
        response = self.client.get(f"{welsh_article_alias.url}/related-data")
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertContains(
            response, f'<link rel="canonical" href="{self.article_series_page.get_full_url()}/related-data">', html=True
        )

    def test_evergreen_route_related_data_translated_welsh_canonical_url(self):
        """Test that translated Welsh article's related data page has Welsh canonical URL."""
        welsh_article = self.article_with_datasets.copy_for_translation(
            locale=Locale.objects.get(language_code="cy"), copy_parents=True
        )
        welsh_article.save_revision().publish()
        response = self.client.get(f"{welsh_article.url}/related-data", headers={"host": "cy.ons.localhost"})
        self.assertEqual(response.status_code, HTTPStatus.OK)
        welsh_series_url = welsh_article.get_parent().get_full_url()
        self.assertContains(response, f'<link rel="canonical" href="{welsh_series_url}/related-data">', html=True)

    def test_evergreen_route_related_data_alternate_urls(self):
        """Test that the related data page has correct hreflang alternate URLs."""
        # TODO: Update tests once bug CMS-765 is resolved.
        # For now, always use the article URL and not the series URL for hreflang links,
        # nor the /related-data suffix.
        welsh_article = self.article_with_datasets.copy_for_translation(
            locale=Locale.objects.get(language_code="cy"), copy_parents=True
        )
        welsh_article.save_revision().publish()
        response = self.client.get(f"{self.article_series_page.url}/related-data", headers={"host": "cy.ons.localhost"})
        self.assertEqual(response.status_code, HTTPStatus.OK)
        # TODO: Change to {self.article_series_page.url}/related-data once CMS-765 is resolved.
        self.assertContains(
            response,
            f'<link rel="alternate" href="{self.article_with_datasets.url}" hreflang="en-gb" />',
            html=True,
        )
        # TODO: Change to {welsh_series_url}/related-data once CMS-765 is resolved.
        self.assertContains(
            response,
            f'<link rel="alternate" href="{welsh_article.url}" hreflang="cy" />',
            html=True,
        )
