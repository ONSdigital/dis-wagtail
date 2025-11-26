from http import HTTPStatus

from django.test import RequestFactory, TestCase, override_settings
from django.utils import timezone
from wagtail.blocks import StreamValue
from wagtail.models import Locale
from wagtail.test.utils import WagtailTestUtils

from cms.articles.tests.factories import ArticleSeriesPageFactory, StatisticalArticlePageFactory
from cms.datasets.blocks import DatasetStoryBlock
from cms.datavis.tests.factories import TableDataFactory


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
            f'<a href="{self.article_series_page.url}/related-data" class="ons-list__link">'
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
                self.article_with_datasets.url
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
        response = self.client.get(f"{welsh_article.url}/related-data")
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
        response = self.client.get(f"{self.article_series_page.url}/related-data")
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


class ArticleSeriesChartDownloadTestCase(WagtailTestUtils, TestCase):
    """Test chart download routes via ArticleSeriesPage evergreen paths."""

    def setUp(self):
        self.series = ArticleSeriesPageFactory()
        table_data = TableDataFactory(
            table_data=[
                ["Category", "Value 1", "Value 2"],
                ["2020", "100", "150"],
                ["2021", "120", "180"],
            ]
        )
        self.article = StatisticalArticlePageFactory(parent=self.series)
        self.article.content = [
            {
                "type": "section",
                "value": {
                    "title": "Chart Section",
                    "content": [
                        {
                            "type": "line_chart",
                            "value": {
                                "title": "Test Chart Title",
                                "subtitle": "Chart subtitle",
                                "theme": "primary",
                                "table": table_data,
                            },
                            "id": "test-chart-id",
                        }
                    ],
                },
            }
        ]
        self.article.save_revision().publish()

    def test_download_chart_success(self):
        """Test successful chart download via series evergreen path."""
        response = self.client.get(f"{self.series.url}/editions/{self.article.slug}/download-chart/test-chart-id")

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(response["Content-Type"], "text/csv")
        self.assertIn("Test Chart Title.csv", response["Content-Disposition"])
        # Check CSV content
        content = response.content.decode("utf-8")
        self.assertIn("Category", content)
        self.assertIn("2020", content)

    def test_download_chart_404_no_edition(self):
        """Test 404 when edition slug doesn't match a live edition."""
        response = self.client.get(f"{self.series.url}/editions/nonexistent-edition/download-chart/test-chart-id")
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    def test_download_chart_404_invalid_chart_id(self):
        """Test 404 when chart_id doesn't exist in the article."""
        response = self.client.get(
            f"{self.series.url}/editions/{self.article.slug}/download-chart/nonexistent-chart-id"
        )
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)


class ArticleSeriesChartDownloadWithVersionTestCase(WagtailTestUtils, TestCase):
    """Test chart download with version routes via ArticleSeriesPage.

    This covers the use case where an article has been corrected and the user
    wants to download a chart from a previous version.
    """

    @classmethod
    def setUpTestData(cls):
        cls.series = ArticleSeriesPageFactory()
        cls.original_table_data = TableDataFactory(
            table_data=[
                ["Category", "Original Value"],
                ["2020", "100"],
            ]
        )
        cls.corrected_table_data = TableDataFactory(
            table_data=[
                ["Category", "Corrected Value"],
                ["2020", "999"],
            ]
        )

    def test_download_chart_with_version_success(self):
        """Test downloading a chart from a previous (corrected) version."""
        # Create article with original chart data
        article = StatisticalArticlePageFactory(parent=self.series)
        article.content = [
            {
                "type": "section",
                "value": {
                    "title": "Chart Section",
                    "content": [
                        {
                            "type": "line_chart",
                            "value": {
                                "title": "Original Chart",
                                "subtitle": "",
                                "theme": "primary",
                                "table": self.original_table_data,
                            },
                            "id": "chart-to-download",
                        }
                    ],
                },
            }
        ]
        article.save_revision().publish()
        original_revision_id = article.latest_revision_id

        # Create a correction with updated chart data
        article.content = [
            {
                "type": "section",
                "value": {
                    "title": "Chart Section",
                    "content": [
                        {
                            "type": "line_chart",
                            "value": {
                                "title": "Corrected Chart",
                                "subtitle": "",
                                "theme": "primary",
                                "table": self.corrected_table_data,
                            },
                            "id": "chart-to-download",
                        }
                    ],
                },
            }
        ]
        article.corrections = [
            {
                "type": "correction",
                "value": {
                    "version_id": 1,
                    "previous_version": original_revision_id,
                    "date": "2024-01-15",
                    "text": "Data correction",
                },
            }
        ]
        article.save_revision().publish()

        # Download the chart from version 1 (the superseded version)
        response = self.client.get(
            f"{self.series.url}/editions/{article.slug}/versions/1/download-chart/chart-to-download"
        )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(response["Content-Type"], "text/csv")
        # The version 1 chart should have the original data
        content = response.content.decode("utf-8")
        self.assertIn("Original Value", content)
        self.assertIn("100", content)
        self.assertNotIn("Corrected Value", content)

        # Download the chart from the latest (corrected) version via the main article path
        latest_response = self.client.get(f"{self.series.url}/editions/{article.slug}/download-chart/chart-to-download")

        self.assertEqual(latest_response.status_code, HTTPStatus.OK)
        # The latest chart should have the corrected data
        latest_content = latest_response.content.decode("utf-8")
        self.assertIn("Corrected Value", latest_content)
        self.assertIn("999", latest_content)
        self.assertNotIn("Original Value", latest_content)

    def test_download_chart_with_version_404_no_edition(self):
        """Test 404 when edition slug doesn't match a live edition."""
        response = self.client.get(
            f"{self.series.url}/editions/nonexistent-edition/versions/1/download-chart/test-chart-id"
        )
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    def test_download_chart_with_version_404_invalid_version(self):
        """Test 404 when version doesn't exist."""
        article = StatisticalArticlePageFactory(parent=self.series)
        article.content = [
            {
                "type": "section",
                "value": {
                    "title": "Chart Section",
                    "content": [
                        {
                            "type": "line_chart",
                            "value": {
                                "title": "Test Chart",
                                "subtitle": "",
                                "theme": "primary",
                                "table": self.original_table_data,
                            },
                            "id": "chart-to-download",
                        }
                    ],
                },
            }
        ]
        article.save_revision().publish()

        # No corrections exist, so version 1 doesn't exist
        response = self.client.get(
            f"{self.series.url}/editions/{article.slug}/versions/1/download-chart/chart-to-download"
        )
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    def test_download_chart_with_version_404_invalid_chart_id(self):
        """Test 404 when chart_id doesn't exist in the versioned article."""
        article = StatisticalArticlePageFactory(parent=self.series)
        article.content = [
            {
                "type": "section",
                "value": {
                    "title": "Chart Section",
                    "content": [
                        {
                            "type": "line_chart",
                            "value": {
                                "title": "Original Chart",
                                "subtitle": "",
                                "theme": "primary",
                                "table": self.original_table_data,
                            },
                            "id": "existing-chart-id",
                        }
                    ],
                },
            }
        ]
        article.save_revision().publish()
        original_revision_id = article.latest_revision_id

        # Add a correction
        article.corrections = [
            {
                "type": "correction",
                "value": {
                    "version_id": 1,
                    "previous_version": original_revision_id,
                    "date": "2024-01-15",
                    "text": "Minor correction",
                },
            }
        ]
        article.save_revision().publish()

        # Try to download a chart that doesn't exist
        response = self.client.get(
            f"{self.series.url}/editions/{article.slug}/versions/1/download-chart/nonexistent-chart-id"
        )
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    def test_download_chart_with_version_404_chart_added_in_correction(self):
        """Test 404 when chart was added in the correction and doesn't exist in the old version."""
        # Create article without any charts
        article = StatisticalArticlePageFactory(parent=self.series)
        article.content = [
            {
                "type": "section",
                "value": {
                    "title": "Text Only Section",
                    "content": [
                        {
                            "type": "rich_text",
                            "value": "<p>Original content without charts</p>",
                        }
                    ],
                },
            }
        ]
        article.save_revision().publish()
        original_revision_id = article.latest_revision_id

        # Add a chart as part of a correction
        article.content = [
            {
                "type": "section",
                "value": {
                    "title": "Chart Section",
                    "content": [
                        {
                            "type": "line_chart",
                            "value": {
                                "title": "New Chart",
                                "subtitle": "",
                                "theme": "primary",
                                "table": self.corrected_table_data,
                            },
                            "id": "new-chart-id",
                        }
                    ],
                },
            }
        ]
        article.corrections = [
            {
                "type": "correction",
                "value": {
                    "version_id": 1,
                    "previous_version": original_revision_id,
                    "date": "2024-01-15",
                    "text": "Added missing chart",
                },
            }
        ]
        article.save_revision().publish()

        # The chart exists in the latest version
        latest_response = self.client.get(f"{self.series.url}/editions/{article.slug}/download-chart/new-chart-id")
        self.assertEqual(latest_response.status_code, HTTPStatus.OK)

        # But the chart doesn't exist in version 1 (the original version without charts)
        response = self.client.get(f"{self.series.url}/editions/{article.slug}/versions/1/download-chart/new-chart-id")
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)
