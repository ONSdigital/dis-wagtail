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
        """Retrieve a specific page dict from the items by matching URI."""
        return next((item for item in data["items"] if item.get("uri") == page.url_path), None)

    def test_resources_returns_200_and_lists_various_page_types(self):
        """Endpoint should return 200 and include all included_pages in the items."""
        response = self.call_view_as_external(RESOURCE_ENDPOINT)
        self.assertEqual(response.status_code, 200, f"Expected 200 OK from {RESOURCE_ENDPOINT}")

        data = self.parse_json(response)
        self.assertIn("items", data, "Response JSON should contain 'items' list")

        for page in self.included_pages:
            matching = self.get_page_dict(data, page)
            self.assertIsNotNone(matching, f"Expected page with URI {page.url_path} to be present in the items")
            self.assert_base_fields(matching, page)

    def test_resources_excludes_non_indexable_pages(self):
        """Non-indexable pages (ArticleSeries, Home, ReleaseCalendarIndex, Theme, Topic)
        should not appear in items.
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
        cls.total_resources = len(cls.pages) + 1  # +1 for the parent

    def call_view_as_external(self, url):
        """Helper to simulate calling the view in an external environment."""
        with override_settings(ROOT_URLCONF="cms.search.tests.test_urls", IS_EXTERNAL_ENV=True):
            return self.client.get(url)

    def parse_json(self, response):
        """Helper to parse JSON from a Django test response."""
        return json.loads(response.content)

    def test_default_pagination_returns_first_slice(self):
        """With no limit/ offset specified we should get DEFAULT_LIMIT (or all if fewer)."""
        response = self.call_view_as_external("/v1/resources/")
        self.assertEqual(response.status_code, 200)

        data = self.parse_json(response)

        expected_items = min(self.total_resources, 20)  # Default page size is 20
        self.assertEqual(len(data["items"]), expected_items)
        self.assertEqual(data["count"], expected_items)
        self.assertEqual(data["total_count"], self.total_resources)
        self.assertEqual(data["offset"], 0)

    def test_second_slice_returns_remaining_items(self):
        """Requesting offset=<7> should return whatever is left after the first slice.
        If the total number of resources is <= 7 the test is skipped.
        """
        min_resources_for_second_slice = 7
        if self.total_resources <= min_resources_for_second_slice:
            self.skipTest("Dataset not large enough to test second slice")

        response = self.call_view_as_external(f"/v1/resources/?offset={7}")
        self.assertEqual(response.status_code, 200)

        data = self.parse_json(response)
        expected_remaining = self.total_resources - 7
        self.assertEqual(len(data["items"]), expected_remaining)
        self.assertEqual(data["count"], expected_remaining)
        self.assertEqual(data["offset"], 7)

    def test_custom_limit_returns_requested_number(self):
        response = self.call_view_as_external("/v1/resources/?limit=5")
        self.assertEqual(response.status_code, 200)

        data = self.parse_json(response)
        self.assertEqual(len(data["items"]), 5)
        self.assertEqual(data["count"], 5)
        self.assertEqual(data["limit"], 5)

    def test_limit_exceeds_max_uses_max(self):
        """When limit exceeds max_limit, results should be capped at max_limit.
        We add enough extra pages to go past MAX_LIMIT of 500.
        """
        extra_needed = 500  # over the cap
        for i in range(extra_needed):
            InformationPageFactory(slug=f"Extra-Page-{i}", parent=self.index_page)

        response = self.call_view_as_external(f"/v1/resources/?limit={500 + 999}")
        self.assertEqual(response.status_code, 200)

        data = self.parse_json(response)
        self.assertEqual(len(data["items"]), 500)
        self.assertEqual(data["count"], 500)
        self.assertEqual(data["limit"], 500)
        self.assertGreater(data["total_count"], 500)
