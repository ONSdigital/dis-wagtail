from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from cms.articles.tests.factories import ArticleSeriesPageFactory, StatisticalArticlePageFactory
from cms.methodology.tests.factories import MethodologyPageFactory
from cms.release_calendar.enums import ReleaseStatus
from cms.release_calendar.tests.factories import ReleaseCalendarPageFactory
from cms.search.tests.helpers import ResourceDictAssertions
from cms.search.utils import build_resource_dict
from cms.standard_pages.tests.factories import IndexPageFactory, InformationPageFactory
from cms.taxonomy.models import GenericPageToTaxonomyTopic, Topic


class ResourceBuildersTestCase(TestCase, ResourceDictAssertions):
    """Tests for resource_builders.py (build_resource_dict and its helpers).
    These tests replicate and consolidate all the “message shape” checks.
    """

    @classmethod
    def setUpTestData(cls):
        cls.info_page = InformationPageFactory(
            title="My Info Page",
            summary="My info page summary",
        )
        cls.methodology_page = MethodologyPageFactory(
            title="Methodology Title",
            summary="Methodology summary",
        )
        cls.index_page = IndexPageFactory(
            title="Index Page Title",
            summary="Index summary",
        )

        cls.release_page_provisional = ReleaseCalendarPageFactory(
            status=ReleaseStatus.PROVISIONAL,
            release_date=timezone.now() - timedelta(minutes=1),
            title="Provisional Release Page",
            summary="Provisional summary",
        )
        cls.release_page_confirmed = ReleaseCalendarPageFactory(
            status=ReleaseStatus.CONFIRMED,
            release_date=timezone.now() - timedelta(minutes=1),
            title="Confirmed Release Page",
            summary="Confirmed summary",
        )
        cls.release_page_cancelled = ReleaseCalendarPageFactory(
            status=ReleaseStatus.CANCELLED,
            release_date=timezone.now() - timedelta(minutes=1),
            title="Cancelled Release Page",
            summary="Cancelled summary",
        )
        cls.release_page_published = ReleaseCalendarPageFactory(
            status=ReleaseStatus.PUBLISHED,
            release_date=timezone.now() - timedelta(minutes=1),
            title="Published Release Page",
            summary="Published summary",
        )

        cls.topic_a = Topic(id="topic-a", title="Topic A")
        Topic.save_new(cls.topic_a)
        cls.topic_b = Topic(id="topic-b", title="Topic B")
        Topic.save_new(cls.topic_b)

        GenericPageToTaxonomyTopic.objects.create(page=cls.info_page, topic=cls.topic_a)
        GenericPageToTaxonomyTopic.objects.create(page=cls.info_page, topic=cls.topic_b)

        cls.article_series = ArticleSeriesPageFactory(title="My Article Series")
        GenericPageToTaxonomyTopic.objects.create(page=cls.article_series, topic=cls.topic_a)
        GenericPageToTaxonomyTopic.objects.create(page=cls.article_series, topic=cls.topic_b)

        cls.article_page = StatisticalArticlePageFactory(
            parent=cls.article_series,
            title="Statistical Article",
            summary="Article summary here",
        )

    # Tests for standard (non-release) pages
    def test_standard_information_page(self):
        """build_resource_dict for an InformationPage should have standard fields,
        correct content_type, and the correct topics (content_type=static_page).
        """
        page = self.info_page
        result = build_resource_dict(page)

        self.assert_base_fields(result, page)
        self.assertIn("release_date", result)

        self.assertEqual(result["topics"], [self.topic_a.id, self.topic_b.id])

    def test_standard_methodology_page(self):
        """MethodologyPage is also a standard page (content_type=static_methodology)."""
        page = self.methodology_page
        result = build_resource_dict(page)

        self.assert_base_fields(result, page)
        self.assertIn("release_date", result)

    def test_index_page(self):
        """IndexPage is also a standard page (content_type=static_landing_page)."""
        page = self.index_page
        result = build_resource_dict(page)
        self.assert_base_fields(result, page)

    def test_release_page_provisional(self):
        """PROVISIONAL status => finalised=True, published=False, cancelled=False, date_changes=[]."""
        page = self.release_page_provisional
        result = build_resource_dict(page)

        self.assert_base_fields(result, page)
        self.assert_release_fields_present(result)
        self.assert_release_booleans(result, finalised=True, cancelled=False, published=False)

    def test_release_page_confirmed(self):
        """CONFIRMED => finalised=True, published=False, cancelled=False."""
        page = self.release_page_confirmed
        result = build_resource_dict(page)

        self.assert_base_fields(result, page)
        self.assert_release_fields_present(result)
        self.assert_release_booleans(result, finalised=True, cancelled=False, published=False)

    def test_release_page_cancelled(self):
        """CANCELLED => cancelled=True, finalised=False, published=False."""
        page = self.release_page_cancelled
        result = build_resource_dict(page)

        self.assert_base_fields(result, page)
        self.assert_release_fields_present(result)
        self.assert_release_booleans(result, finalised=False, cancelled=True, published=False)

    def test_release_page_published(self):
        """PUBLISHED => published=True, finalised=False, cancelled=False."""
        page = self.release_page_published
        result = build_resource_dict(page)

        self.assert_base_fields(result, page)
        self.assert_release_fields_present(result)
        self.assert_release_booleans(result, finalised=False, cancelled=False, published=True)

    def test_release_page_release_date_vs_provisional_date(self):
        """If release_date is set, we do NOT expect 'provisional_date' in the result
        (it can be present only if release_date is None but release_date_text is set).
        """
        page = self.release_page_confirmed
        result = build_resource_dict(page)
        self.assertIn("release_date", result)
        self.assertIsNotNone(result["release_date"])
        self.assertNotIn("provisional_date", result)

    def test_release_page_provisional_date_when_no_release_date(self):
        """If release_date=None but release_date_text is set, we expect 'provisional_date'
        and no 'release_date'.
        """
        page = ReleaseCalendarPageFactory(
            status=ReleaseStatus.PROVISIONAL,
            release_date=None,
            release_date_text="Provisional release date text",
        )
        result = build_resource_dict(page)

        self.assertIsNone(result["release_date"])
        self.assertEqual(result["provisional_date"], page.release_date_text)

    def test_release_page_with_date_changes(self):
        """If changes_to_release_date is present, they should appear in 'date_changes' with
        {previous_date, change_notice}.
        """
        page = ReleaseCalendarPageFactory(
            status=ReleaseStatus.CONFIRMED,
            release_date=timezone.now(),
            title="Confirmed With Changes",
        )
        page.changes_to_release_date = [
            {
                "type": "date_change_log",
                "value": {
                    "previous_date": timezone.now() - timedelta(days=5),
                    "reason_for_change": "Reason 1",
                },
            },
            {
                "type": "date_change_log",
                "value": {
                    "previous_date": timezone.now() - timedelta(days=10),
                    "reason_for_change": "Reason 2",
                },
            },
            {
                "type": "date_change_log",
                "value": {"previous_date": timezone.now() - timedelta(days=15), "reason_for_change": "Reason 3"},
            },
        ]
        page.save()

        result = build_resource_dict(page)

        self.assert_base_fields(result, page)
        self.assert_release_fields_present(result)
        self.assertEqual(len(result["date_changes"]), 3)

        for i, date_change in enumerate(result["date_changes"]):
            self.assertIn("previous_date", date_change)
            self.assertIn("change_notice", date_change)

            expected_value = page.changes_to_release_date[i].value
            self.assertEqual(date_change["change_notice"], expected_value["reason_for_change"])

            # Compare ignoring microseconds
            date_change_val = timezone.datetime.fromisoformat(date_change["previous_date"]).replace(microsecond=0)
            page_val = expected_value["previous_date"].replace(microsecond=0)
            self.assertEqual(date_change_val, page_val)

    def test_article_page_inherits_topics(self):
        """A StatisticalArticlePage typically inherits topics from its parent
        ArticleSeriesPage. Confirm that build_resource_dict picks those up.
        """
        article_data = build_resource_dict(self.article_page)

        self.assert_base_fields(article_data, self.article_page)
        self.assertEqual(article_data["topics"], [self.topic_a.id, self.topic_b.id])
