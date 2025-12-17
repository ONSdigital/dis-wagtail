# pylint: disable=too-many-lines
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
        self.assertIn("test-chart-title.csv", response["Content-Disposition"])
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

    def test_download_chart_404_unpublished_article(self):
        """Test 404 when attempting to download chart from an unpublished article."""
        # Create an article with a chart
        table_data = TableDataFactory(
            table_data=[
                ["Category", "Value"],
                ["2020", "100"],
            ]
        )
        unpublished_article = StatisticalArticlePageFactory(parent=self.series)
        unpublished_article.content = [
            {
                "type": "section",
                "value": {
                    "title": "Chart Section",
                    "content": [
                        {
                            "type": "line_chart",
                            "value": {
                                "title": "Unpublished Chart",
                                "subtitle": "",
                                "theme": "primary",
                                "table": table_data,
                            },
                            "id": "unpublished-chart-id",
                        }
                    ],
                },
            }
        ]
        unpublished_article.save_revision().publish()

        # Now unpublish the article
        unpublished_article.live = False
        unpublished_article.save()

        # Attempt to download the chart - should return 404
        response = self.client.get(
            f"{self.series.url}/editions/{unpublished_article.slug}/download-chart/unpublished-chart-id"
        )
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    def test_download_chart_404_draft_chart_in_published_article(self):
        """Test 404 when attempting to download chart from draft version of a published article."""
        # Create an article with a chart and publish it
        published_table_data = TableDataFactory(
            table_data=[
                ["Category", "Value"],
                ["2020", "100"],
            ]
        )
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
                                "title": "Published Chart",
                                "subtitle": "",
                                "theme": "primary",
                                "table": published_table_data,
                            },
                            "id": "published-chart-id",
                        }
                    ],
                },
            }
        ]
        article.save_revision().publish()

        # Now create a draft revision with a new chart
        draft_table_data = TableDataFactory(
            table_data=[
                ["Category", "Value"],
                ["2021", "200"],
            ]
        )
        article.content = [
            {
                "type": "section",
                "value": {
                    "title": "Chart Section",
                    "content": [
                        {
                            "type": "line_chart",
                            "value": {
                                "title": "Published Chart",
                                "subtitle": "",
                                "theme": "primary",
                                "table": published_table_data,
                            },
                            "id": "published-chart-id",
                        },
                        {
                            "type": "line_chart",
                            "value": {
                                "title": "Draft Chart",
                                "subtitle": "",
                                "theme": "primary",
                                "table": draft_table_data,
                            },
                            "id": "draft-chart-id",
                        },
                    ],
                },
            }
        ]
        article.save_revision()

        # Attempt to download the published chart - should succeed
        response = self.client.get(f"{self.series.url}/editions/{article.slug}/download-chart/published-chart-id")
        self.assertEqual(response.status_code, HTTPStatus.OK)

        # Attempt to download the draft chart - should return 404
        response = self.client.get(f"{self.series.url}/editions/{article.slug}/download-chart/draft-chart-id")
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    def test_download_chart_multiple_charts_in_article(self):
        """Test that correct chart is returned when article has multiple charts."""
        # Create table data for both charts
        first_table_data = TableDataFactory(
            table_data=[
                ["Category", "Value 1", "Value 2"],
                ["2020", "100", "150"],
                ["2021", "120", "180"],
            ]
        )
        second_table_data = TableDataFactory(
            table_data=[
                ["Month", "Sales"],
                ["January", "500"],
                ["February", "750"],
            ]
        )
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
                                "table": first_table_data,
                            },
                            "id": "test-chart-id",
                        },
                        {
                            "type": "line_chart",
                            "value": {
                                "title": "Second Chart Title",
                                "subtitle": "Second chart subtitle",
                                "theme": "primary",
                                "table": second_table_data,
                            },
                            "id": "second-chart-id",
                        },
                    ],
                },
            }
        ]
        self.article.save_revision().publish()

        # Download first chart
        first_response = self.client.get(f"{self.series.url}/editions/{self.article.slug}/download-chart/test-chart-id")
        self.assertEqual(first_response.status_code, HTTPStatus.OK)
        first_content = first_response.content.decode("utf-8")

        # Download second chart
        second_response = self.client.get(
            f"{self.series.url}/editions/{self.article.slug}/download-chart/second-chart-id"
        )
        self.assertEqual(second_response.status_code, HTTPStatus.OK)
        second_content = second_response.content.decode("utf-8")

        # Verify first chart has its data
        self.assertIn("Category", first_content)
        self.assertIn("2020", first_content)
        self.assertNotIn("Month", first_content)
        self.assertNotIn("January", first_content)

        # Verify second chart has its data
        self.assertIn("Month", second_content)
        self.assertIn("January", second_content)
        self.assertIn("500", second_content)
        self.assertNotIn("Category", second_content)
        self.assertNotIn("2020", second_content)

    def test_download_chart_same_id_different_articles(self):
        """Test that same chart_id in different articles returns correct data for each."""
        # Create a second article with a chart using the same ID but different data
        second_article_table_data = TableDataFactory(
            table_data=[
                ["Region", "Population"],
                ["London", "9000000"],
                ["Manchester", "550000"],
            ]
        )
        second_article = StatisticalArticlePageFactory(parent=self.series)
        second_article.content = [
            {
                "type": "section",
                "value": {
                    "title": "Chart Section",
                    "content": [
                        {
                            "type": "line_chart",
                            "value": {
                                "title": "Second Article Chart",
                                "subtitle": "Different data",
                                "theme": "primary",
                                "table": second_article_table_data,
                            },
                            "id": "test-chart-id",  # Same ID as first article's chart
                        }
                    ],
                },
            }
        ]
        second_article.save_revision().publish()

        # Download chart from first article
        first_response = self.client.get(f"{self.series.url}/editions/{self.article.slug}/download-chart/test-chart-id")
        self.assertEqual(first_response.status_code, HTTPStatus.OK)
        first_content = first_response.content.decode("utf-8")

        # Download chart from second article
        second_response = self.client.get(
            f"{self.series.url}/editions/{second_article.slug}/download-chart/test-chart-id"
        )
        self.assertEqual(second_response.status_code, HTTPStatus.OK)
        second_content = second_response.content.decode("utf-8")

        # Verify first article's chart has its data
        self.assertIn("Category", first_content)
        self.assertIn("2020", first_content)
        self.assertIn("100", first_content)
        self.assertNotIn("Region", first_content)
        self.assertNotIn("London", first_content)

        # Verify second article's chart has its data
        self.assertIn("Region", second_content)
        self.assertIn("London", second_content)
        self.assertIn("9000000", second_content)
        self.assertNotIn("Category", second_content)
        self.assertNotIn("2020", second_content)


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

    def test_download_with_version_zero_returns_404(self):
        """Test that requesting version 0 returns 404."""
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
                            "id": "chart-id",
                        }
                    ],
                },
            }
        ]
        article.save_revision().publish()

        response = self.client.get(f"{self.series.url}/editions/{article.slug}/versions/0/download-chart/chart-id")
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)


class ArticleSeriesChartDownloadMultilingualTestCase(WagtailTestUtils, TestCase):
    """Test chart download with multi-lingual support (Welsh translations and aliases)."""

    def setUp(self):
        self.series = ArticleSeriesPageFactory()
        self.table_data = TableDataFactory(
            table_data=[
                ["Category", "Value"],
                ["2020", "100"],
                ["2021", "200"],
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
                                "title": "Test Chart",
                                "subtitle": "Chart subtitle",
                                "theme": "primary",
                                "table": self.table_data,
                            },
                            "id": "test-chart-id",
                        }
                    ],
                },
            }
        ]
        self.article.save_revision().publish()

    def test_download_chart_from_welsh_alias(self):
        """Test that chart download works from Welsh alias article."""
        # Create Welsh alias
        welsh_article_alias = self.article.copy_for_translation(
            locale=Locale.objects.get(language_code="cy"),
            copy_parents=True,  # Ensure Welsh series is created
            alias=True,
        )

        welsh_series = welsh_article_alias.get_parent().specific
        response = self.client.get(
            f"{welsh_series.url}/editions/{welsh_article_alias.slug}/download-chart/test-chart-id"
        )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(response["Content-Type"], "text/csv")
        self.assertIn("test-chart.csv", response["Content-Disposition"])

        content = response.content.decode("utf-8")
        self.assertIn("Category", content)
        self.assertIn("2020", content)
        self.assertIn("100", content)

    def test_download_chart_from_welsh_translation(self):
        """Test that chart download works from fully translated Welsh article."""
        # Create Welsh translation (full translation, not just an alias)
        welsh_article = self.article.copy_for_translation(
            locale=Locale.objects.get(language_code="cy"), copy_parents=True
        )
        welsh_article.save_revision().publish()

        welsh_series = welsh_article.get_parent().specific
        response = self.client.get(f"{welsh_series.url}/editions/{welsh_article.slug}/download-chart/test-chart-id")

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(response["Content-Type"], "text/csv")
        self.assertIn("test-chart.csv", response["Content-Disposition"])

        content = response.content.decode("utf-8")
        self.assertIn("Category", content)
        self.assertIn("2020", content)
        self.assertIn("100", content)

    def test_download_chart_welsh_translation_with_different_data(self):
        """Test that Welsh translation with different chart data returns the correct data."""
        # Create a new English article with different data first
        english_table_data_2 = TableDataFactory(
            table_data=[
                ["Category", "Value 2"],
                ["2020", "300"],
                ["2021", "400"],
            ]
        )
        english_article_2 = StatisticalArticlePageFactory(parent=self.series)
        english_article_2.content = [
            {
                "type": "section",
                "value": {
                    "title": "Chart Section 2",
                    "content": [
                        {
                            "type": "line_chart",
                            "value": {
                                "title": "Test Chart 2",
                                "subtitle": "Chart subtitle 2",
                                "theme": "primary",
                                "table": english_table_data_2,
                            },
                            "id": "test-chart-id-2",
                        }
                    ],
                },
            }
        ]
        english_article_2.save_revision().publish()

        # Create Welsh translation with different chart data
        welsh_table_data = TableDataFactory(
            table_data=[
                ["Categori", "Gwerth"],
                ["2020", "150"],
                ["2021", "250"],
            ]
        )

        welsh_article = english_article_2.copy_for_translation(
            locale=Locale.objects.get(language_code="cy"), copy_parents=True, alias=False
        )
        welsh_article.content = [
            {
                "type": "section",
                "value": {
                    "title": "Adran Siart",
                    "content": [
                        {
                            "type": "line_chart",
                            "value": {
                                "title": "Siart Prawf",
                                "subtitle": "Is-deitl y siart",
                                "theme": "primary",
                                "table": welsh_table_data,
                            },
                            "id": "test-chart-id-2",
                        }
                    ],
                },
            }
        ]
        welsh_article.save_revision().publish()

        # Download chart from English article
        english_response = self.client.get(
            f"{self.series.url}/editions/{english_article_2.slug}/download-chart/test-chart-id-2"
        )
        english_content = english_response.content.decode("utf-8")

        # Download chart from Welsh article
        welsh_series = welsh_article.get_parent().specific
        welsh_response = self.client.get(
            f"{welsh_series.url}/editions/{welsh_article.slug}/download-chart/test-chart-id-2"
        )
        welsh_content = welsh_response.content.decode("utf-8")

        # Verify both downloads succeed
        self.assertEqual(english_response.status_code, HTTPStatus.OK)
        self.assertEqual(welsh_response.status_code, HTTPStatus.OK)

        # Verify English article has English data
        self.assertIn("Category", english_content)
        self.assertIn("300", english_content)
        self.assertNotIn("Categori", english_content)
        self.assertNotIn("150", english_content)

        # Verify Welsh article has Welsh data
        self.assertIn("Categori", welsh_content)
        self.assertIn("150", welsh_content)
        self.assertNotIn("Value 2", welsh_content)
        self.assertNotIn("300", welsh_content)

    def test_download_chart_404_when_chart_not_in_welsh_translation(self):
        """Test that 404 is returned when chart doesn't exist in Welsh translation."""
        # Create Welsh translation without the chart
        welsh_article = self.article.copy_for_translation(
            locale=Locale.objects.get(language_code="cy"), copy_parents=True, alias=False
        )
        welsh_article.content = [
            {
                "type": "section",
                "value": {
                    "title": "Adran Testun",
                    "content": [
                        {
                            "type": "rich_text",
                            "value": "<p>Dim siart yma</p>",
                        }
                    ],
                },
            }
        ]
        welsh_article.save_revision().publish()

        # Attempt to download chart that doesn't exist in Welsh translation
        welsh_series = welsh_article.get_parent().specific
        response = self.client.get(f"{welsh_series.url}/editions/{welsh_article.slug}/download-chart/test-chart-id")
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    def test_download_chart_welsh_translation_with_version(self):
        """Test downloading versioned chart from fully translated Welsh article."""
        # Create Welsh translation with original chart data
        welsh_article = self.article.copy_for_translation(
            locale=Locale.objects.get(language_code="cy"), copy_parents=True, alias=False
        )
        welsh_table_data = TableDataFactory(
            table_data=[
                ["Categori", "Gwerth"],
                ["2020", "100"],
            ]
        )
        welsh_article.content = [
            {
                "type": "section",
                "value": {
                    "title": "Adran Siart",
                    "content": [
                        {
                            "type": "line_chart",
                            "value": {
                                "title": "Siart",
                                "subtitle": "",
                                "theme": "primary",
                                "table": welsh_table_data,
                            },
                            "id": "test-chart-id",
                        }
                    ],
                },
            }
        ]
        welsh_article.save_revision().publish()
        original_revision_id = welsh_article.latest_revision_id

        # Create a correction with updated Welsh chart data
        corrected_welsh_table_data = TableDataFactory(
            table_data=[
                ["Categori", "Gwerth Cywir"],
                ["2020", "999"],
            ]
        )
        welsh_article.content = [
            {
                "type": "section",
                "value": {
                    "title": "Adran Siart",
                    "content": [
                        {
                            "type": "line_chart",
                            "value": {
                                "title": "Siart Cywir",
                                "subtitle": "",
                                "theme": "primary",
                                "table": corrected_welsh_table_data,
                            },
                            "id": "test-chart-id",
                        }
                    ],
                },
            }
        ]
        welsh_article.corrections = [
            {
                "type": "correction",
                "value": {
                    "version_id": 1,
                    "previous_version": original_revision_id,
                    "date": "2024-01-15",
                    "text": "Cywiriad data",
                },
            }
        ]
        welsh_article.save_revision().publish()

        # Get the Welsh series
        welsh_series = welsh_article.get_parent().specific

        # Download the original version (version 1)
        response = self.client.get(
            f"{welsh_series.url}/editions/{welsh_article.slug}/versions/1/download-chart/test-chart-id"
        )

        self.assertEqual(response.status_code, HTTPStatus.OK)

        # Verify we get the original Welsh data, not the corrected data
        content = response.content.decode("utf-8")
        self.assertIn("Gwerth", content)
        self.assertIn("100", content)
        self.assertNotIn("Gwerth Cywir", content)
        self.assertNotIn("999", content)
