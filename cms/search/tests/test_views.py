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

        cls.topic_a = Topic(id="topic-a", title="Topic A")
        Topic.save_new(cls.topic_a)

        cls.topic_b = Topic(id="topic-b", title="Topic B")
        Topic.save_new(cls.topic_b)

        cls.info_page = InformationPage(title="My Info Page", summary="My info page summary")
        cls.index_page.add_child(instance=cls.info_page)
        cls.info_page.save()

        # Add topics to the information page
        GenericPageToTaxonomyTopic.objects.create(page=cls.info_page, topic=cls.topic_a)
        GenericPageToTaxonomyTopic.objects.create(page=cls.info_page, topic=cls.topic_b)

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
            self.assertIsNotNone(matching_page)

            self.assertEqual(matching_page.get("title"), page.title)
            self.assertEqual(matching_page.get("content_type"), expected_type)
            self.assertEqual(matching_page.get("summary"), page.summary)

    def test_resources_result_information_page_with_topics(self):
        """InformationPage with topics should include topic titles in the results."""
        response = self.call_view_as_external("/v1/resources/")
        self.assertEqual(response.status_code, 200, "Expected 200 OK from /v1/resources/")
        data = json.loads(response.content)
        self.assertIn("results", data, "Response JSON should contain 'results' list")
        expected_type = EXPECTED_CONTENT_TYPES[type(self.info_page).__name__]

        matching_page = next((item for item in data["results"] if item.get("uri") == self.info_page.url_path), None)
        self.assertIsNotNone(matching_page)

        self.assertEqual(matching_page.get("title"), self.info_page.title)
        self.assertEqual(matching_page.get("content_type"), expected_type)
        self.assertEqual(matching_page.get("summary"), self.info_page.summary)
        self.assertEqual(matching_page.get("topics"), [self.topic_a.id, self.topic_b.id])

    # def test_resources_result_release_page_provisional_confirmed(self):

    # def test_resources_result_release_date_exists_provisional_date_absent(self):

    # def test_resources_result_provisional_date_exists_when_release_date_absent(self):

    # def test_resources_result_release_page_confirmed_date_change(self):

    # def test_resources_result_release_page_published(self):

    # def test_resources_result_release_page_cancelled(self):

    # def test_resources_article_page_with_inherited_topics(self):

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

    # def test_resources_result_structure_and_fields(self):
    #     """Each result should contain the expected fields per the search API contract."""
    #     # Create one example page of each main type to inspect fields
    #     release = ReleaseCalendarPageFactory(title="Release Fields Test")
    #     release.finalised = False
    #     release.published = False
    #     release.cancelled = False
    #     release.release_date = "2025-03-01T00:00:00Z"
    #     release.provisional_date = "2025-04-01T00:00:00Z"  # simulate a provisional future date
    #     release.save()
    #     methodology = MethodologyPageFactory(title="Methodology Fields Test", release_date="2024-12-12T00:00:00Z")
    #     info = InformationPageFactory(title="Static Fields Test")

    #     # Optionally assign a topic to one of them for topic field test (will also test separately below)
    #     topic_page = None
    #     try:
    #         theme = ThemePageFactory(title="Health")
    #         topic_page = TopicPageFactory(title="Nutrition", parent=theme)
    #         # Assign the topic to the release page (assuming a ManyToMany relation like release.topics)
    #         if hasattr(release, "topics"):
    #             release.topics.add(topic_page)
    #             release.save()
    #     except Exception:
    #         # If topic assignment fails (perhaps due to model differences), we'll handle in separate topic test
    #         topic_page = None

    #     response = self.client.get("/v1/resources/")
    #     data = json.loads(response.content)
    #     self.assertEqual(response.status_code, 200)
    #     results = data.get("results", [])
    #     # Find our specific pages in results
    #     release_item = next((item for item in results if item.get("title") == "Release Fields Test"), None)
    #     meth_item = next((item for item in results if item.get("title") == "Methodology Fields Test"), None)
    #     info_item = next((item for item in results if item.get("title") == "Static Fields Test"), None)
    #     self.assertIsNotNone(release_item, "Release page should be in results")
    #     self.assertIsNotNone(meth_item, "Methodology page should be in results")
    #     self.assertIsNotNone(info_item, "Static page should be in results")

    #     # Common fields present in all
    #     for item in (release_item, meth_item, info_item):
    #         for field in ("title", "summary", "uri", "type"):
    #             self.assertIn(field, item, f"Every result item should have '{field}' field")

    #     # Check release-specific fields
    #     # Release should have release_date, finalised, published, cancelled, date_changes, provisional_date
    #     for field in ("release_date", "finalised", "published", "cancelled", "date_changes"):
    #         self.assertIn(field, release_item, f"Release result missing '{field}'")
    #     # provisional_date should be present because we set one
    #     self.assertIn("provisional_date", release_item, "Release result missing 'provisional_date'")
    #     # Verify the values match what was set
    #     self.assertEqual(release_item["finalised"], False)
    #     self.assertEqual(release_item["published"], False)
    #     self.assertEqual(release_item["cancelled"], False)
    #     self.assertEqual(release_item["release_date"], "2025-03-01T00:00:00Z")
    #     self.assertEqual(release_item.get("provisional_date"), "2025-04-01T00:00:00Z")
    #     # date_changes likely an empty list since none were explicitly added
    #     self.assertIn("date_changes", release_item)
    #     self.assertIsInstance(release_item["date_changes"], list)
    #     # (If date_changes were added, we would verify their structure here)

    #     # Check that methodology has release_date but not release-only extras
    #     self.assertIn("release_date", meth_item, "Methodology result should have 'release_date'")
    #     self.assertNotIn("finalised", meth_item, "Methodology result should not have 'finalised'")
    #     self.assertNotIn("published", meth_item, "Methodology result should not have 'published'")
    #     self.assertNotIn("cancelled", meth_item, "Methodology result should not have 'cancelled'")
    #     self.assertNotIn("provisional_date", meth_item, "Methodology result should not have 'provisional_date'")
    #     self.assertNotIn("date_changes", meth_item, "Methodology result should not have 'date_changes'")

    #     # Check that static page has no release_date or release fields (assuming static pages don't have those)
    #     self.assertNotIn("release_date", info_item, "Static page result should not have 'release_date'")
    #     self.assertNotIn("finalised", info_item, "Static page result should not have 'finalised'")
    #     self.assertNotIn("published", info_item, "Static page result should not have 'published'")
    #     self.assertNotIn("cancelled", info_item, "Static page result should not have 'cancelled'")
    #     self.assertNotIn("provisional_date", info_item, "Static page result should not have 'provisional_date'")
    #     self.assertNotIn("date_changes", info_item, "Static page result should not have 'date_changes'")

    #     # If topic was assigned to release, verify topics field
    #     if topic_page:
    #         self.assertIn("topics", release_item, "Topics field should be present when topics are assigned")
    #         self.assertIsInstance(release_item["topics"], list)
    #         self.assertIn("Nutrition", release_item["topics"], "Assigned topic name should appear in topics list")

    # def test_resources_includes_topics_in_results(self):
    #     """Topics assigned to pages should be reflected in the results."""
    #     # Create a theme and topic, then a page with that topic.
    #     theme = ThemePageFactory(title="Population")
    #     topic = TopicPageFactory(title="Census", parent=theme)
    #     # Create an indexable page and assign the topic (if the page model has a topics relation)
    #     page = InformationPageFactory(title="Topic Test Page")
    #     if hasattr(page, "topics"):
    #         page.topics.add(topic)
    #         page.save()
    #     else:
    #         # If InformationPage does not have topics, use a release or methodology page for this test
    #         page = ReleaseCalendarPageFactory(
    #             title="Topic Test Release",
    #             topics=[topic] if "topics" in ReleaseCalendarPageFactory._meta.model.__dict__ else None,
    #         )
    #         # Ensure it's published
    #         page.release_date = "2025-05-01T00:00:00Z"
    #         page.save()
    #         if not hasattr(page, "topics"):
    #             # If even release doesn't have a topics field (unlikely), skip test
    #             self.skipTest("No topics field available to test topic inclusion.")

    #     response = self.client.get("/v1/resources")
    #     data = json.loads(response.content)
    #     result_item = next((item for item in data.get("results", []) if item.get("title") == page.title), None)
    #     self.assertIsNotNone(result_item, "The page with topics should be present in results")
    #     # The topics field should include the topic's title
    #     self.assertIn("topics", result_item, "Result item should have 'topics' key")
    #     topics_list = result_item["topics"]
    #     self.assertIsInstance(topics_list, list, "Topics field should be a list")
    #     self.assertIn("Census", topics_list, "Topics list should contain the assigned topic name")

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
