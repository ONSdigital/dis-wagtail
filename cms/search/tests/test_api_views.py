from unittest.mock import patch

import factory
from django.conf import settings
from django.test import TestCase, override_settings

from cms.articles.tests.factories import ArticleSeriesPageFactory, StatisticalArticlePageFactory
from cms.home.models import HomePage
from cms.methodology.tests.factories import MethodologyPageFactory
from cms.release_calendar.models import ReleaseCalendarIndex
from cms.release_calendar.tests.factories import ReleaseCalendarPageFactory
from cms.search.tests.helpers import ExternalAPITestMixin, ResourceDictAssertions
from cms.search.utils import build_page_uri
from cms.standard_pages.tests.factories import IndexPageFactory, InformationPageFactory
from cms.themes.tests.factories import ThemePageFactory
from cms.topics.tests.factories import TopicPageFactory

RESOURCE_ENDPOINT = "/v1/resources/"


@override_settings(IS_EXTERNAL_ENV=False)
class SearchResourcesViewTests(TestCase, ResourceDictAssertions, ExternalAPITestMixin):
    @classmethod
    def setUpTestData(cls):
        # Pages that are excluded from the search index
        cls.excluded_pages = [
            ArticleSeriesPageFactory(),
            HomePage(),
            ReleaseCalendarIndex(),
            ThemePageFactory(),
            TopicPageFactory(),
            InformationPageFactory(parent=IndexPageFactory(slug="custom-slug-0"), live=False),  # Not live
        ]

        # Pages that are included in the search index
        cls.included_pages = [
            InformationPageFactory(),
            MethodologyPageFactory(),
            ReleaseCalendarPageFactory(),
            StatisticalArticlePageFactory(),
            IndexPageFactory(slug="custom-slug-1"),
        ]

    @staticmethod
    def get_page_dict(data, page):
        """Retrieve a specific page dict from the items by matching URI."""
        return next((item for item in data["items"] if item.get("uri") == build_page_uri(page)), None)

    def test_resources_returns_200_and_lists_various_page_types(self):
        """Endpoint should return 200 and include all included_pages in the items."""
        response = self.client.get(RESOURCE_ENDPOINT)
        self.assertEqual(response.status_code, 200, f"Expected 200 OK from {RESOURCE_ENDPOINT}")

        data = self.parse_json(response)
        self.assertIn("items", data, "Response JSON should contain 'items' list")

        for page in self.included_pages:
            matching = self.get_page_dict(data, page)
            self.assertIsNotNone(matching, f"Expected page with URI {build_page_uri(page)} to be present in the items")
            self.assert_base_fields(matching, page)

    def test_resources_excludes_non_indexable_pages(self):
        """Non-indexable pages (ArticleSeries, Home, ReleaseCalendarIndex, Theme, Topic)
        should not appear in items.
        """
        response = self.client.get(RESOURCE_ENDPOINT)
        self.assertEqual(response.status_code, 200)

        data = self.parse_json(response)
        for page in self.excluded_pages:
            self.assertIsNone(
                self.get_page_dict(data, page),
                f"Expected page with URI {build_page_uri(page)} not to be present",
            )

    def test_resources_available_in_external_env(self):
        """Endpoint should return 200 when IS_EXTERNAL_ENV=True."""
        response = self.call_view_as_external(RESOURCE_ENDPOINT)
        self.assertEqual(response.status_code, 200)


@override_settings(IS_EXTERNAL_ENV=False)
class ResourceListViewPaginationTests(TestCase, ExternalAPITestMixin):
    @classmethod
    def setUpTestData(cls):
        cls.index_page = IndexPageFactory(slug="custom-slug-1")
        # One parent + 12 child pages = 13 total
        cls.pages = InformationPageFactory.create_batch(
            12, parent=cls.index_page, slug=factory.Sequence(lambda n: f"test_page_{n + 1}")
        )
        cls.total_resources = len(cls.pages) + 1  # +1 for the parent

    def test_default_pagination_returns_first_slice(self):
        """With no limit/ offset specified we should get DEFAULT_LIMIT (or all if fewer)."""
        response = self.client.get(RESOURCE_ENDPOINT)
        self.assertEqual(response.status_code, 200)

        data = self.parse_json(response)

        expected_items = min(
            self.total_resources, settings.SEARCH_API_DEFAULT_PAGE_SIZE
        )  # Default page size is 20 currently
        self.assertEqual(len(data["items"]), expected_items)
        self.assertEqual(data["count"], expected_items)
        self.assertEqual(data["total_count"], self.total_resources)
        self.assertEqual(data["offset"], 0)

    def test_second_slice_returns_remaining_items(self):
        """Requesting offset=<7> should return whatever is left after the first slice."""
        response = self.client.get(f"{RESOURCE_ENDPOINT}?offset=7")
        self.assertEqual(response.status_code, 200)

        data = self.parse_json(response)
        expected_remaining = self.total_resources - 7
        self.assertEqual(len(data["items"]), expected_remaining)
        self.assertEqual(data["count"], expected_remaining)
        self.assertEqual(data["offset"], 7)

    def test_custom_limit_returns_requested_number(self):
        response = self.client.get(f"{RESOURCE_ENDPOINT}?limit=5")
        self.assertEqual(response.status_code, 200)

        data = self.parse_json(response)
        self.assertEqual(len(data["items"]), 5)
        self.assertEqual(data["count"], 5)
        self.assertEqual(data["limit"], 5)

    @patch("cms.search.pagination.CustomLimitOffsetPagination.max_limit", 10)
    def test_limit_exceeds_max_uses_max(self):
        """When limit exceeds max_limit, results should be capped at max_limit.
        We add enough extra pages to go past MAX_LIMIT of 20.
        """
        response = self.client.get(f"{RESOURCE_ENDPOINT}?limit=30")
        self.assertEqual(response.status_code, 200)

        data = self.parse_json(response)
        self.assertEqual(len(data["items"]), 10)
        self.assertEqual(data["count"], 10)
        self.assertEqual(data["limit"], 10)
        self.assertEqual(data["total_count"], self.total_resources)
