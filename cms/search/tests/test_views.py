import json

from django.test import TestCase, override_settings

from cms.articles.tests.factories import ArticleSeriesPageFactory, StatisticalArticlePageFactory
from cms.home.models import HomePage
from cms.methodology.tests.factories import MethodologyPageFactory
from cms.release_calendar.models import ReleaseCalendarIndex
from cms.release_calendar.tests.factories import ReleaseCalendarPageFactory
from cms.search.tests.helpers import ResourceDictAssertions
from cms.standard_pages.tests.factories import IndexPageFactory, InformationPageFactory
from cms.themes.tests.factories import ThemePageFactory
from cms.topics.tests.factories import TopicPageFactory

RESOURCE_ENDPOINT = "/v1/resources/"


@override_settings(IS_EXTERNAL_ENV=False)
class SearchResourcesViewTests(TestCase, ResourceDictAssertions):
    @classmethod
    def setUpTestData(cls):
        # Pages that are excluded from the search index
        cls.excluded_pages = [
            ArticleSeriesPageFactory(),
            HomePage(),
            ReleaseCalendarIndex(),
            ThemePageFactory(),
            TopicPageFactory(),
        ]

        # Pages that are included in the search index
        cls.included_pages = [
            InformationPageFactory(),
            MethodologyPageFactory(),
            ReleaseCalendarPageFactory(),
            StatisticalArticlePageFactory(),
            IndexPageFactory(slug="custom-slug-1"),
        ]

    def call_view_as_external(self, url):
        """Helper to simulate calling the view in an external environment."""
        with override_settings(ROOT_URLCONF="cms.search.tests.test_urls", IS_EXTERNAL_ENV=True):
            return self.client.get(url)

    def parse_json(self, response):
        """Helper to parse JSON from a Django test response."""
        return json.loads(response.content)

    def get_page_dict(self, data, page):
        """Retrieve a specific page dict from the results by matching URI."""
        return next((item for item in data["results"] if item.get("uri") == page.url_path), None)

    def test_resources_returns_200_and_lists_various_page_types(self):
        """Endpoint should return 200 and include all included_pages in the results."""
        response = self.call_view_as_external(RESOURCE_ENDPOINT)
        self.assertEqual(response.status_code, 200, f"Expected 200 OK from {RESOURCE_ENDPOINT}")

        data = self.parse_json(response)
        self.assertIn("results", data, "Response JSON should contain 'results' list")

        for page in self.included_pages:
            matching = self.get_page_dict(data, page)
            self.assertIsNotNone(matching, f"Expected page with URI {page.url_path} to be present in the results")
            self.assert_base_fields(matching, page)

    def test_resources_excludes_non_indexable_pages(self):
        """Non-indexable pages (ArticleSeries, Home, ReleaseCalendarIndex, Theme, Topic)
        should not appear in results.
        """
        response = self.call_view_as_external(RESOURCE_ENDPOINT)
        self.assertEqual(response.status_code, 200)

        data = self.parse_json(response)
        for page in self.excluded_pages:
            self.assertIsNone(
                self.get_page_dict(data, page), f"Expected page with URI {page.url_path} not to be present"
            )

    def test_resources_disabled_when_external_env_false(self):
        """Endpoint should return 404 when IS_EXTERNAL_ENV=False."""
        response = self.client.get(RESOURCE_ENDPOINT)
        self.assertEqual(response.status_code, 404)


@override_settings(IS_EXTERNAL_ENV=False)
class ResourceListViewPaginationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.index_page = IndexPageFactory(slug="custom-slug-1")
        # One parent + 12 child pages = 13 total
        cls.pages = [InformationPageFactory(slug=f"Page-{i}", parent=cls.index_page) for i in range(12)]

    def call_view_as_external(self, url):
        """Helper to simulate calling the view in an external environment."""
        with override_settings(ROOT_URLCONF="cms.search.tests.test_urls", IS_EXTERNAL_ENV=True):
            return self.client.get(url)

    def parse_json(self, response):
        """Helper to parse JSON from a Django test response."""
        return json.loads(response.content)

    def test_default_pagination_returns_first_10(self):
        """Should return the first 10 items by default (page_size=10)."""
        response = self.call_view_as_external("/v1/resources/")
        self.assertEqual(response.status_code, 200)

        data = self.parse_json(response)
        self.assertEqual(len(data["results"]), 10)
        self.assertEqual(data["count"], 13)
        self.assertIsNone(data["previous"])
        self.assertIsNotNone(data["next"])

    def test_second_page_returns_remaining_items(self):
        """Page=2 should return the remaining 3 items (since total=13, default page_size=10)."""
        response = self.call_view_as_external("/v1/resources/?page=2")
        self.assertEqual(response.status_code, 200)

        data = self.parse_json(response)
        self.assertEqual(len(data["results"]), 3)
        self.assertEqual(data["count"], 13)

    def test_custom_page_size_returns_requested_number(self):
        """page_size=5 returns 5 items."""
        response = self.call_view_as_external("/v1/resources/?page_size=5")
        self.assertEqual(response.status_code, 200)

        data = self.parse_json(response)
        self.assertEqual(len(data["results"]), 5)
        self.assertEqual(data["count"], 13)

    def test_page_size_exceeds_max_uses_max(self):
        """When page_size exceeds max_page_size=100, results should be capped at 100."""
        # Add extra 120 pages to exceed the maximum
        for i in range(120):
            InformationPageFactory(slug=f"Page-{12 + i}", parent=self.index_page)

        response = self.call_view_as_external("/v1/resources/?page_size=999")
        self.assertEqual(response.status_code, 200)

        data = self.parse_json(response)
        self.assertEqual(len(data["results"]), 100)
        self.assertEqual(data["count"], 133)
