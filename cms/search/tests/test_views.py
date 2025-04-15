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
        # Pages that are in SEARCH_INDEX_EXCLUDED_PAGE_TYPES
        cls.excluded_pages = [
            ArticleSeriesPageFactory(),
            HomePage(),
            ReleaseCalendarIndex(),
            ThemePageFactory(),
            TopicPageFactory(),
        ]

        # Pages that are NOT in SEARCH_INDEX_EXCLUDED_PAGE_TYPES
        cls.included_pages = [
            InformationPageFactory(),
            MethodologyPageFactory(),
            ReleaseCalendarPageFactory(),
            StatisticalArticlePageFactory(),
            IndexPageFactory(slug="custom-slug-1"),
        ]

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

        cls.index_page = cls.included_pages[0].get_parent()
        cls.article_series = cls.included_pages[3].get_parent()

        cls.topic_a = Topic(id="topic-a", title="Topic A")
        Topic.save_new(cls.topic_a)

        cls.topic_b = Topic(id="topic-b", title="Topic B")
        Topic.save_new(cls.topic_b)

        cls.info_page = InformationPage(title="My Info Page", summary="My info page summary")

    def call_view_as_external(self, url):
        with override_settings(IS_EXTERNAL_ENV=True):
            return self.client.get(url)

    def test_resources_returns_200_and_lists_various_page_types(self):
        """Endpoint should return 200 and include all included_pages in the setUpTestData."""
        response = self.call_view_as_external("/v1/resources/")
        self.assertEqual(response.status_code, 200, "Expected 200 OK from /v1/resources/")
        data = json.loads(response.content)
        self.assertIn("results", data, "Response JSON should contain 'results' list")

        for page in self.included_pages:
            expected_type = EXPECTED_CONTENT_TYPES[type(page).__name__]

            matching_page = next((item for item in data["results"] if item.get("uri") == page.url_path), None)

            self.assertIsNotNone(matching_page, f"Expected page with URI {page.url_path} to be present in the results")

            self.assertEqual(matching_page.get("title"), page.title)
            self.assertEqual(matching_page.get("content_type"), expected_type)
            self.assertEqual(matching_page.get("summary"), page.summary)

    def test_resources_result_information_page_with_topics(self):
        """InformationPage with topics should include topic titles in the results."""
        self.index_page.add_child(instance=self.info_page)
        self.info_page.save()

        # Add topics to the information page
        GenericPageToTaxonomyTopic.objects.create(page=self.info_page, topic=self.topic_a)
        GenericPageToTaxonomyTopic.objects.create(page=self.info_page, topic=self.topic_b)

        response = self.call_view_as_external("/v1/resources/")
        self.assertEqual(response.status_code, 200, "Expected 200 OK from /v1/resources/")
        data = json.loads(response.content)
        self.assertIn("results", data, "Response JSON should contain 'results' list")
        expected_type = EXPECTED_CONTENT_TYPES[type(self.info_page).__name__]

        matching_page = next((item for item in data["results"] if item.get("uri") == self.info_page.url_path), None)

        self.assertIsNotNone(
            matching_page, f"Expected page with URI {self.info_page.url_path} to be present in the results"
        )

        self.assertEqual(matching_page.get("title"), self.info_page.title)
        self.assertEqual(matching_page.get("content_type"), expected_type)
        self.assertEqual(matching_page.get("summary"), self.info_page.summary)
        self.assertEqual(matching_page.get("topics"), [self.topic_a.id, self.topic_b.id])

    def test_resources_result_release_page_provisional_confirmed(self):
        """Ensure that for a release-type page, release-specific fields are included in the results."""
        release_calendar_pages = [
            self.release_calendar_page_provisional,
            self.release_calendar_page_confirmed,
        ]

        response = self.call_view_as_external("/v1/resources/")
        self.assertEqual(response.status_code, 200, "Expected 200 OK from /v1/resources/")
        data = json.loads(response.content)
        self.assertIn("results", data, "Response JSON should contain 'results' list")

        for page in release_calendar_pages:
            expected_type = EXPECTED_CONTENT_TYPES[type(page).__name__]

            matching_page = next((item for item in data["results"] if item.get("uri") == page.url_path), None)

            self.assertIsNotNone(matching_page, f"Expected page with URI {page.url_path} to be present in the results")

            self.assertEqual(matching_page.get("content_type"), expected_type)
            self.assertEqual(matching_page.get("title"), page.title)
            self.assertEqual(matching_page.get("summary"), page.summary)
            self.assertEqual(matching_page.get("uri"), page.url_path)

            self.assertIsNotNone(matching_page.get("release_date"), "Release date should be present for release pages")
            self.assertEqual(matching_page.get("release_date"), page.release_date.isoformat())

            self.assertIn("finalised", matching_page)
            self.assertIn("cancelled", matching_page)
            self.assertIn("published", matching_page)

            self.assertTrue(matching_page.get("finalised"), "Finalised should be True for provisional/confirmed pages")
            self.assertFalse(
                matching_page.get("published"), "Published should be False for provisional/confirmed pages"
            )
            self.assertFalse(
                matching_page.get("cancelled"), "Cancelled should be False for provisional/confirmed pages"
            )

    def test_resources_result_release_date_exists_provisional_date_absent(self):
        """Ensure that if release_date exists, provisional_date should not exist."""
        page = self.release_calendar_page_confirmed
        response = self.call_view_as_external("/v1/resources/")
        self.assertEqual(response.status_code, 200, "Expected 200 OK from /v1/resources/")
        data = json.loads(response.content)
        self.assertIn("results", data, "Response JSON should contain 'results' list")

        matching_page = next((item for item in data["results"] if item.get("uri") == page.url_path), None)
        self.assertIsNotNone(matching_page, f"Expected page with URI {page.url_path} to be present in the results")

        expected_type = EXPECTED_CONTENT_TYPES[type(page).__name__]
        self.assertEqual(matching_page["content_type"], expected_type)
        self.assertEqual(matching_page["title"], page.title)
        self.assertEqual(matching_page["summary"], page.summary)
        self.assertEqual(matching_page["uri"], page.url_path)

        # Check release_date exists
        self.assertIsNotNone(matching_page.get("release_date"), "release_date should exist for this page")
        self.assertEqual(matching_page["release_date"], page.release_date.isoformat())

        # Check provisional_date does not exist
        self.assertIsNone(
            matching_page.get("provisional_date"), "provisional_date should not exist if release_date exists"
        )

    def test_resources_result_provisional_date_exists_when_release_date_absent(self):
        """Ensure that if release_date is absent, provisional_date should exist and have a value."""
        page = ReleaseCalendarPageFactory(
            status=ReleaseStatus.PROVISIONAL,
            release_date=None,
            release_date_text="Provisional release date text",
        )

        response = self.call_view_as_external("/v1/resources/")
        self.assertEqual(response.status_code, 200, "Expected 200 OK from /v1/resources/")
        data = json.loads(response.content)
        self.assertIn("results", data, "Response JSON should contain 'results' list")

        matching_page = next((item for item in data["results"] if item.get("uri") == page.url_path), None)
        self.assertIsNotNone(matching_page, f"Expected page with URI {page.url_path} to be present in the results")

        expected_type = EXPECTED_CONTENT_TYPES[type(page).__name__]
        self.assertEqual(matching_page["content_type"], expected_type)
        self.assertEqual(matching_page["title"], page.title)
        self.assertEqual(matching_page["summary"], page.summary)
        self.assertEqual(matching_page["uri"], page.url_path)

        # Check release_date is absent
        self.assertIsNone(matching_page.get("release_date"), "release_date should be None for this page")

        # Check provisional_date exists and has the correct value
        self.assertIsNotNone(
            matching_page.get("provisional_date"), "provisional_date should exist if release_date is absent"
        )
        self.assertEqual(matching_page["provisional_date"], page.release_date_text)

    def test_resources_result_release_page_confirmed_date_change(self):
        """Ensure that for a release-type page, release-specific fields get added."""
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

        response = self.call_view_as_external("/v1/resources/")
        self.assertEqual(response.status_code, 200, "Expected 200 OK from /v1/resources/")
        data = json.loads(response.content)
        self.assertIn("results", data, "Response JSON should contain 'results' list")

        matching_page = next((item for item in data["results"] if item.get("uri") == page.url_path), None)
        self.assertIsNotNone(matching_page, f"Expected page with URI {page.url_path} to be present in the results")

        expected_type = EXPECTED_CONTENT_TYPES[type(page).__name__]
        self.assertEqual(matching_page["content_type"], expected_type)
        self.assertEqual(matching_page["title"], page.title)
        self.assertEqual(matching_page["summary"], page.summary)
        self.assertEqual(matching_page["uri"], page.url_path)

        self.assertIsNotNone(matching_page["release_date"], "release_date should exist for this page")
        self.assertEqual(matching_page["release_date"], page.release_date.isoformat())

        self.assertIn("finalised", matching_page)
        self.assertIn("cancelled", matching_page)
        self.assertIn("published", matching_page)

        self.assertTrue(matching_page["finalised"], "Finalised should be True for confirmed pages")
        self.assertFalse(matching_page["published"], "Published should be False for confirmed pages")
        self.assertFalse(matching_page["cancelled"], "Cancelled should be False for confirmed pages")

        self.assertIn("date_changes", matching_page, "date_changes should be present in the results")
        self.assertEqual(len(matching_page["date_changes"]), 3, "Expected 3 date changes in the results")

        for i, date_change in enumerate(matching_page["date_changes"]):
            # The test only checks string equality at the microsecond level,
            # any slight storage/serialization difference can make the test fail
            # The fix is her is to compare datetimes in a way that ignores microseconds
            # so we do not rely on real microsecond precision.
            api_dt = timezone.datetime.fromisoformat(date_change["previous_date"])
            expected_page_dt = page.changes_to_release_date[i].value["previous_date"]

            self.assertEqual(date_change["change_notice"], page.changes_to_release_date[i].value["reason_for_change"])
            self.assertEqual(
                api_dt.replace(microsecond=0),
                expected_page_dt.replace(microsecond=0),
                "Expected date change to match the page's date change",
            )

    def test_resources_result_release_page_published(self):
        """Ensure that for a release-type page, release-specific fields get added."""
        page = self.release_calendar_page_published

        response = self.call_view_as_external("/v1/resources/")
        self.assertEqual(response.status_code, 200, "Expected 200 OK from /v1/resources/")
        data = json.loads(response.content)
        self.assertIn("results", data, "Response JSON should contain 'results' list")

        matching_page = next((item for item in data["results"] if item.get("uri") == page.url_path), None)
        self.assertIsNotNone(matching_page, f"Expected page with URI {page.url_path} to be present in the results")

        expected_type = EXPECTED_CONTENT_TYPES[type(page).__name__]
        self.assertEqual(matching_page["content_type"], expected_type)
        self.assertEqual(matching_page["title"], page.title)
        self.assertEqual(matching_page["summary"], page.summary)
        self.assertEqual(matching_page["uri"], page.url_path)

        self.assertIsNotNone(matching_page["release_date"], "release_date should exist for this page")
        self.assertEqual(matching_page["release_date"], page.release_date.isoformat())

        self.assertIn("finalised", matching_page)
        self.assertIn("cancelled", matching_page)
        self.assertIn("published", matching_page)

        self.assertFalse(matching_page["finalised"], "Finalised should be False for published pages")
        self.assertTrue(matching_page["published"], "Published should be True for published pages")
        self.assertFalse(matching_page["cancelled"], "Cancelled should be False for published pages")

    def test_resources_result_release_page_cancelled(self):
        """Ensure that for a release-type page, release-specific fields get added."""
        page = self.release_calendar_page_cancelled

        response = self.call_view_as_external("/v1/resources/")
        self.assertEqual(response.status_code, 200, "Expected 200 OK from /v1/resources/")
        data = json.loads(response.content)
        self.assertIn("results", data, "Response JSON should contain 'results' list")

        matching_page = next((item for item in data["results"] if item.get("uri") == page.url_path), None)
        self.assertIsNotNone(matching_page, f"Expected page with URI {page.url_path} to be present in the results")

        expected_type = EXPECTED_CONTENT_TYPES[type(page).__name__]
        self.assertEqual(matching_page["content_type"], expected_type)
        self.assertEqual(matching_page["title"], page.title)
        self.assertEqual(matching_page["summary"], page.summary)
        self.assertEqual(matching_page["uri"], page.url_path)

        self.assertIsNotNone(matching_page["release_date"], "release_date should exist for this page")
        self.assertEqual(matching_page["release_date"], page.release_date.isoformat())

        self.assertIn("finalised", matching_page)
        self.assertIn("cancelled", matching_page)
        self.assertIn("published", matching_page)

        self.assertFalse(matching_page["finalised"], "Finalised should be False for cancelled pages")
        self.assertFalse(matching_page["published"], "Published should be False for cancelled pages")
        self.assertTrue(matching_page["cancelled"], "Cancelled should be True for cancelled pages")

    def test_resources_article_page_with_inherited_topics(self):
        """Ensure that the article page contains topics inherited from the parent article series."""
        GenericPageToTaxonomyTopic.objects.create(page=self.article_series, topic=self.topic_a)
        GenericPageToTaxonomyTopic.objects.create(page=self.article_series, topic=self.topic_b)

        # Create a StatisticalArticlePage under the ArticleSeriesPage
        self.article_page = StatisticalArticlePageFactory(
            parent=self.article_series, title="Statistical Article", summary="Article summary"
        )

        response = self.call_view_as_external("/v1/resources/")
        self.assertEqual(response.status_code, 200, "Expected 200 OK from /v1/resources/")
        data = json.loads(response.content)
        self.assertIn("results", data, "Response JSON should contain 'results' list")

        matching_page = next((item for item in data["results"] if item.get("uri") == self.article_page.url_path), None)
        self.assertIsNotNone(
            matching_page, f"Expected page with URI {self.article_page.url_path} to be present in the results"
        )

        expected_type = EXPECTED_CONTENT_TYPES[type(self.article_page).__name__]
        self.assertEqual(matching_page["content_type"], expected_type)
        self.assertEqual(matching_page["title"], self.article_page.title)
        self.assertEqual(matching_page["summary"], self.article_page.summary)
        self.assertEqual(matching_page["uri"], self.article_page.url_path)

        # Ensure the topics are inherited from the parent ArticleSeriesPage
        self.assertEqual(matching_page["topics"], [self.topic_a.id, self.topic_b.id])

    def test_resources_excludes_non_indexable_pages(self):
        """Non-indexable pages (ArticleSeries, Home, ReleaseCalendarIndex, Theme, Topic)
        should not appear in results.
        """
        response = self.call_view_as_external("/v1/resources/")
        self.assertEqual(response.status_code, 200, "Expected 200 OK from /v1/resources/")
        data = json.loads(response.content)
        self.assertIn("results", data, "Response JSON should contain 'results' list")

        for page in self.excluded_pages:
            # Check that excluded pages are not in the results
            expected_uri = page.url_path
            matching_page = next((item for item in data["results"] if item.get("uri") == expected_uri), None)
            self.assertIsNone(matching_page, f"Expected page with URI {expected_uri} to NOT be present in the results")

    def test_resources_disabled_when_external_env_false(self):
        """Endpoint should return 404 when IS_EXTERNAL_ENV is False."""
        # Even if content exists, the endpoint should be inaccessible in this setting.
        response = self.client.get("/v1/resources/")
        self.assertEqual(response.status_code, 404, "Expected 404 when IS_EXTERNAL_ENV=False")
        self.assertEqual(response.json()["detail"], "Not found.")


@override_settings(IS_EXTERNAL_ENV=False)
class ResourceListViewPaginationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.index_page = IndexPageFactory(slug="custom-slug-1")
        cls.pages = [InformationPageFactory(slug=f"Page-{i}", parent=cls.index_page) for i in range(12)]

    def call_view_as_external(self, url):
        with override_settings(IS_EXTERNAL_ENV=True):
            return self.client.get(url)

    def test_default_pagination_returns_first_10(self):
        """Should return the first 10 items by default (page_size=10)."""
        response = self.call_view_as_external("/v1/resources/")
        data = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(data["results"]), 10)
        self.assertIn("next", data)
        self.assertIn("previous", data)
        self.assertEqual(data["previous"], None)
        self.assertIsNotNone(data["next"])
        self.assertEqual(data["count"], 13)

    def test_second_page_returns_remaining_items(self):
        """Second page should return the remaining 2 items."""
        response = self.call_view_as_external("/v1/resources/?page=2")
        data = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(data["results"]), 3)
        self.assertEqual(data["count"], 13)

    def test_custom_page_size_returns_requested_number(self):
        """Custom page size should override the default."""
        response = self.call_view_as_external("/v1/resources/?page_size=5")
        data = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(data["results"]), 5)
        self.assertEqual(data["count"], 13)

    def test_page_size_exceeds_max_uses_max(self):
        """When page_size exceeds max_page_size=100, it should cap at 100."""
        for i in range(120):
            InformationPageFactory(slug=f"Page-{12 + i}", parent=self.index_page)

        response = self.call_view_as_external("/v1/resources/?page_size=999")
        data = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(data["results"]), 100)
        self.assertEqual(data["count"], 133)
