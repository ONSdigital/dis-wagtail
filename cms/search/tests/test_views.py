import json
from datetime import timedelta

from django.test import TestCase, override_settings
from django.utils import timezone

from cms.articles.tests.factories import ArticleSeriesPageFactory, StatisticalArticlePageFactory
from cms.home.models import HomePage
from cms.methodology.tests.factories import MethodologyPageFactory
from cms.release_calendar.enums import ReleaseStatus
from cms.release_calendar.models import ReleaseCalendarIndex
from cms.release_calendar.tests.factories import ReleaseCalendarPageFactory
from cms.standard_pages.models import InformationPage  # Uses GenericTaxonomyMixin
from cms.standard_pages.tests.factories import IndexPageFactory, InformationPageFactory
from cms.taxonomy.models import GenericPageToTaxonomyTopic, Topic
from cms.themes.tests.factories import ThemePageFactory
from cms.topics.tests.factories import TopicPageFactory

RESOURCE_ENDPOINT = "/v1/resources/"
EXPECTED_CONTENT_TYPES = {
    "ReleaseCalendarPage": "release",
    "StatisticalArticlePage": "bulletin",
    "InformationPage": "static_page",
    "IndexPage": "static_landing_page",
    "MethodologyPage": "static_methodology",
}


@override_settings(IS_EXTERNAL_ENV=False)
class SearchResourcesViewTests(TestCase):
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

        # Different ReleaseCalendarPages with various statuses
        cls.release_calendar_page_provisional = ReleaseCalendarPageFactory(
            status=ReleaseStatus.PROVISIONAL,
            release_date=timezone.now() - timedelta(minutes=1),
        )
        cls.release_calendar_page_confirmed = ReleaseCalendarPageFactory(
            status=ReleaseStatus.CONFIRMED,
            release_date=timezone.now() - timedelta(minutes=1),
        )
        cls.release_calendar_page_cancelled = ReleaseCalendarPageFactory(
            status=ReleaseStatus.CANCELLED,
            release_date=timezone.now() - timedelta(minutes=1),
        )
        cls.release_calendar_page_published = ReleaseCalendarPageFactory(
            status=ReleaseStatus.PUBLISHED,
            release_date=timezone.now() - timedelta(minutes=1),
        )

        # Parents
        cls.index_page = cls.included_pages[0].get_parent()
        cls.article_series = cls.included_pages[3].get_parent()

        # Topics
        cls.topic_a = Topic(id="topic-a", title="Topic A")
        Topic.save_new(cls.topic_a)

        cls.topic_b = Topic(id="topic-b", title="Topic B")
        Topic.save_new(cls.topic_b)

        # Additional page for topic testing
        cls.info_page = InformationPage(title="My Info Page", summary="My info page summary")

    def call_view_as_external(self, url):
        """Helper to simulate calling the view in an external environment."""
        with override_settings(IS_EXTERNAL_ENV=True):
            return self.client.get(url)

    def parse_json(self, response):
        """Helper to parse JSON from a Django test response."""
        return json.loads(response.content)

    def get_page_dict(self, data, page):
        """Retrieve a specific page dict from the results by matching URI."""
        return next((item for item in data["results"] if item.get("uri") == page.url_path), None)

    def assert_page_basic_fields(self, page_dict, page):
        """Assert basic fields on a returned page dict match the actual page."""
        expected_type = EXPECTED_CONTENT_TYPES[type(page).__name__]
        self.assertEqual(page_dict.get("content_type"), expected_type)
        self.assertEqual(page_dict.get("title"), page.title)
        self.assertEqual(page_dict.get("summary"), page.summary)
        self.assertEqual(page_dict.get("uri"), page.url_path)

    def test_resources_returns_200_and_lists_various_page_types(self):
        """Endpoint should return 200 and include all included_pages in the results."""
        response = self.call_view_as_external(RESOURCE_ENDPOINT)
        self.assertEqual(response.status_code, 200, f"Expected 200 OK from {RESOURCE_ENDPOINT}")

        data = self.parse_json(response)
        self.assertIn("results", data, "Response JSON should contain 'results' list")

        for page in self.included_pages:
            matching = self.get_page_dict(data, page)
            self.assertIsNotNone(matching, f"Expected page with URI {page.url_path} to be present in the results")
            self.assert_page_basic_fields(matching, page)

    def test_resources_result_information_page_with_topics(self):
        """InformationPage with topics should include those topic IDs in the results."""
        self.index_page.add_child(instance=self.info_page)
        self.info_page.save()

        # Add topics
        GenericPageToTaxonomyTopic.objects.create(page=self.info_page, topic=self.topic_a)
        GenericPageToTaxonomyTopic.objects.create(page=self.info_page, topic=self.topic_b)

        response = self.call_view_as_external(RESOURCE_ENDPOINT)
        self.assertEqual(response.status_code, 200)

        data = self.parse_json(response)
        matching = self.get_page_dict(data, self.info_page)
        self.assertIsNotNone(matching)

        self.assert_page_basic_fields(matching, self.info_page)
        self.assertEqual(matching.get("topics"), [self.topic_a.id, self.topic_b.id])

    def test_resources_result_release_page_provisional_confirmed(self):
        """For release pages (provisional/ confirmed), release-specific fields should appear."""
        release_calendar_pages = [self.release_calendar_page_provisional, self.release_calendar_page_confirmed]
        response = self.call_view_as_external(RESOURCE_ENDPOINT)
        self.assertEqual(response.status_code, 200)

        data = self.parse_json(response)
        for page in release_calendar_pages:
            matching = self.get_page_dict(data, page)
            self.assertIsNotNone(matching)

            self.assert_page_basic_fields(matching, page)
            self.assertIsNotNone(matching.get("release_date"), "Release date should be present for release pages")
            self.assertEqual(matching["release_date"], page.release_date.isoformat())

            # Check status booleans
            self.assertTrue(matching["finalised"])
            self.assertFalse(matching["published"])
            self.assertFalse(matching["cancelled"])

    def test_resources_result_release_date_exists_provisional_date_absent(self):
        """If release_date is set, provisional_date should not be present."""
        page = self.release_calendar_page_confirmed
        response = self.call_view_as_external(RESOURCE_ENDPOINT)
        self.assertEqual(response.status_code, 200)

        data = self.parse_json(response)
        matching = self.get_page_dict(data, page)
        self.assertIsNotNone(matching)

        self.assert_page_basic_fields(matching, page)
        self.assertIsNotNone(matching.get("release_date"))
        self.assertIsNone(matching.get("provisional_date"))

    def test_resources_result_provisional_date_exists_when_release_date_absent(self):
        """If release_date is absent, provisional_date should exist (for provisional status)."""
        page = ReleaseCalendarPageFactory(
            status=ReleaseStatus.PROVISIONAL,
            release_date=None,
            release_date_text="Provisional release date text",
        )

        response = self.call_view_as_external(RESOURCE_ENDPOINT)
        self.assertEqual(response.status_code, 200)

        data = self.parse_json(response)
        matching = self.get_page_dict(data, page)
        self.assertIsNotNone(matching)

        self.assert_page_basic_fields(matching, page)
        self.assertIsNone(matching.get("release_date"))
        self.assertEqual(matching.get("provisional_date"), page.release_date_text)

    def test_resources_result_release_page_confirmed_date_change(self):
        """Confirmed page with changes_to_release_date should return date_changes array."""
        page = self.release_calendar_page_confirmed
        page.changes_to_release_date = [
            {
                "type": "date_change_log",
                "value": {"previous_date": timezone.now() - timedelta(days=5), "reason_for_change": "Reason 1"},
            },
            {
                "type": "date_change_log",
                "value": {"previous_date": timezone.now() - timedelta(days=10), "reason_for_change": "Reason 2"},
            },
            {
                "type": "date_change_log",
                "value": {"previous_date": timezone.now() - timedelta(days=15), "reason_for_change": "Reason 3"},
            },
        ]
        page.save()

        response = self.call_view_as_external(RESOURCE_ENDPOINT)
        self.assertEqual(response.status_code, 200)

        data = self.parse_json(response)
        matching = self.get_page_dict(data, page)
        self.assertIsNotNone(matching)

        self.assert_page_basic_fields(matching, page)
        self.assertTrue(matching["finalised"])
        self.assertFalse(matching["published"])
        self.assertFalse(matching["cancelled"])

        self.assertIn("date_changes", matching)
        self.assertEqual(len(matching["date_changes"]), 3)

        for i, date_change in enumerate(matching["date_changes"]):
            api_dt_str = date_change["previous_date"]
            reason = date_change["change_notice"]

            page_previous_date = page.changes_to_release_date[i].value["previous_date"]
            page_reason = page.changes_to_release_date[i].value["reason_for_change"]

            # Compare ignoring microseconds
            api_dt = timezone.datetime.fromisoformat(api_dt_str).replace(microsecond=0)
            page_dt = page_previous_date.replace(microsecond=0)

            self.assertEqual(api_dt, page_dt)
            self.assertEqual(reason, page_reason)

    def test_resources_result_release_page_published(self):
        """A published release page should have release_date, published=True,
        and finalised /cancelled=False.
        """
        page = self.release_calendar_page_published
        response = self.call_view_as_external(RESOURCE_ENDPOINT)
        self.assertEqual(response.status_code, 200)

        data = self.parse_json(response)
        matching = self.get_page_dict(data, page)
        self.assertIsNotNone(matching)

        self.assert_page_basic_fields(matching, page)
        self.assertIsNotNone(matching.get("release_date"))
        self.assertFalse(matching["finalised"])
        self.assertTrue(matching["published"])
        self.assertFalse(matching["cancelled"])

    def test_resources_result_release_page_cancelled(self):
        """A cancelled release page should have release_date, cancelled=True,
        and finalised/published=False.
        """
        page = self.release_calendar_page_cancelled
        response = self.call_view_as_external(RESOURCE_ENDPOINT)
        self.assertEqual(response.status_code, 200)

        data = self.parse_json(response)
        matching = self.get_page_dict(data, page)
        self.assertIsNotNone(matching)

        self.assert_page_basic_fields(matching, page)
        self.assertTrue(matching["cancelled"])
        self.assertFalse(matching["finalised"])
        self.assertFalse(matching["published"])

    def test_resources_article_page_with_inherited_topics(self):
        """StatisticalArticlePage should inherit topics from its parent ArticleSeriesPage."""
        GenericPageToTaxonomyTopic.objects.create(page=self.article_series, topic=self.topic_a)
        GenericPageToTaxonomyTopic.objects.create(page=self.article_series, topic=self.topic_b)

        article_page = StatisticalArticlePageFactory(
            parent=self.article_series, title="Statistical Article", summary="Article summary"
        )

        response = self.call_view_as_external(RESOURCE_ENDPOINT)
        self.assertEqual(response.status_code, 200)

        data = self.parse_json(response)
        matching = self.get_page_dict(data, article_page)
        self.assertIsNotNone(matching)

        self.assert_page_basic_fields(matching, article_page)
        # Ensure the topics are inherited from the parent
        self.assertEqual(matching.get("topics"), [self.topic_a.id, self.topic_b.id])

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
        # Although content exists, the endpoint should be inaccessible in this setting.
        response = self.client.get(RESOURCE_ENDPOINT)
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["detail"], "Not found.")


@override_settings(IS_EXTERNAL_ENV=False)
class ResourceListViewPaginationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.index_page = IndexPageFactory(slug="custom-slug-1")
        # One parent + 12 child pages = 13 total
        cls.pages = [InformationPageFactory(slug=f"Page-{i}", parent=cls.index_page) for i in range(12)]

    def call_view_as_external(self, url):
        """Helper to simulate calling the view in an external environment."""
        with override_settings(IS_EXTERNAL_ENV=True):
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
