import logging
from datetime import timedelta
from unittest.mock import ANY, MagicMock, patch

from django.test import TestCase, override_settings
from django.utils import timezone
from wagtail.models import Page
from wagtail.test.utils import WagtailTestUtils

from cms.articles.tests.factories import ArticleSeriesPageFactory, StatisticalArticlePageFactory
from cms.methodology.tests.factories import MethodologyPageFactory
from cms.release_calendar.enums import ReleaseStatus
from cms.release_calendar.tests.factories import ReleaseCalendarPageFactory
from cms.search.publishers import BasePublisher, KafkaPublisher, LogPublisher
from cms.standard_pages.models import InformationPage  # Uses GenericTaxonomyMixin
from cms.standard_pages.tests.factories import IndexPageFactory, InformationPageFactory
from cms.taxonomy.models import GenericPageToTaxonomyTopic, Topic

EXPECTED_CONTENT_TYPES = {
    "ReleaseCalendarPage": "release",
    "StatisticalArticlePage": "bulletin",
    "InformationPage": "static_page",
    "IndexPage": "static_landing_page",
    "MethodologyPage": "static_methodology",
}


class DummyPublisher(BasePublisher):
    """Concrete subclass of BasePublisher for testing the shared functionality."""

    def __init__(self, channel_created_or_updated, channel_deleted):
        self._channel_created_or_updated = channel_created_or_updated
        self._channel_deleted = channel_deleted

    @property
    def created_or_updated_channel(self) -> str | None:
        return self._channel_created_or_updated

    @property
    def deleted_channel(self) -> str | None:
        return self._channel_deleted

    def _publish(self, channel, message):
        # We don't actually publish in tests; we just want to spy on the calls.
        pass


class BasePublisherTestCase(TestCase):
    """Base TestCase providing helper methods for checking the messages
    sent to publishers.
    """

    def assert_page_message_fields(self, message, page):
        """Assert that the message dict from a publisher call has the correct basic fields
        (uri, title, summary, content_type) matching the given page.
        """
        expected_type = EXPECTED_CONTENT_TYPES[type(page).__name__]

        self.assertIn("uri", message, "Message dict missing 'uri'")
        self.assertIn("title", message, "Message dict missing 'title'")
        self.assertIn("summary", message, "Message dict missing 'summary'")
        self.assertIn("content_type", message, "Message dict missing 'content_type'")
        self.assertIn("topics", message, "Message dict missing 'topics'")

        self.assertEqual(message["uri"], page.url_path)
        self.assertEqual(message["title"], page.title)
        self.assertEqual(message["summary"], page.summary)
        self.assertEqual(message["content_type"], expected_type)

    def assert_release_page_fields(self, message, page):
        """Additional assertions for release-type pages (release_date, finalised, cancelled, published, etc.)."""
        self.assertIn("release_date", message, "Message dict missing 'release_date' for release page")
        self.assertIn("finalised", message, "Message dict missing 'finalised' field")
        self.assertIn("cancelled", message, "Message dict missing 'cancelled' field")
        self.assertIn("published", message, "Message dict missing 'published' field")

        self.assertEqual(message["release_date"], page.release_date.isoformat())

    def assert_date_changes(self, message, page):
        """If the page has date_changes, verify they match the page's changes_to_release_date entries."""
        self.assertIn("date_changes", message)
        self.assertEqual(len(message["date_changes"]), len(page.changes_to_release_date))

        for i, date_change in enumerate(message["date_changes"]):
            expected_value = page.changes_to_release_date[i].value
            self.assertIn("previous_date", date_change, "date_change missing 'previous_date'")
            self.assertIn("change_notice", date_change, "date_change missing 'change_notice'")

            self.assertEqual(date_change["change_notice"], expected_value["reason_for_change"])
            self.assertEqual(
                date_change["previous_date"],
                expected_value["previous_date"].isoformat(),
            )


class BasePublisherTests(BasePublisherTestCase, WagtailTestUtils):
    @classmethod
    def setUpTestData(cls):
        cls.superuser = cls.create_superuser(username="admin")
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

        cls.publisher = DummyPublisher(
            channel_created_or_updated="dummy-channel-created",
            channel_deleted="dummy-channel-deleted",
        )

        cls.root_page = Page.objects.get(id=1)

        cls.topic_a = Topic(id="topic-a", title="Topic A")
        Topic.save_new(cls.topic_a)

        cls.topic_b = Topic(id="topic-b", title="Topic B")
        Topic.save_new(cls.topic_b)

        cls.info_page = InformationPage(title="My Info Page", summary="My info page summary")
        cls.root_page.add_child(instance=cls.info_page)
        cls.info_page.save()

        # Add topics to the information page
        GenericPageToTaxonomyTopic.objects.create(page=cls.info_page, topic=cls.topic_a)
        GenericPageToTaxonomyTopic.objects.create(page=cls.info_page, topic=cls.topic_b)

    @patch.object(DummyPublisher, "_publish", return_value=None)
    def test_publish_created_or_updated_calls_publish(self, mock_method):
        """Verify `publish_created_or_updated` calls `_publish` with correct channel & message."""
        for page in self.included_pages:
            self.publisher.publish_created_or_updated(page)

            # The channel should come from created_or_updated_channel
            mock_method.assert_called_once()
            channel_called, message_called = mock_method.call_args[0]

            self.assertEqual(channel_called, "dummy-channel-created")
            self.assert_page_message_fields(message_called, page)

            mock_method.reset_mock()

    @patch.object(DummyPublisher, "_publish", return_value=None)
    def test_publish_deleted_calls_publish(self, mock_method):
        """Verify `publish_deleted` calls `_publish` with the correct channel & message."""
        for page in self.included_pages:
            self.publisher.publish_deleted(page)

            mock_method.assert_called_once()
            channel_called, message_called = mock_method.call_args[0]

            self.assertEqual(channel_called, "dummy-channel-deleted")
            self.assertIn("uri", message_called)
            self.assertEqual(message_called["uri"], page.url_path)

            mock_method.reset_mock()

    def test_construct_message_for_release_page_provisional_confirmed(self):
        """For release pages (provisional/confirmed), release-specific fields should appear."""
        release_calendar_pages = [
            self.release_calendar_page_provisional,
            self.release_calendar_page_confirmed,
        ]
        for page in release_calendar_pages:
            message = self.publisher._construct_message_for_create_update(page)  # pylint: disable=W0212
            self.assert_page_message_fields(message, page)
            self.assert_release_page_fields(message, page)

            # finalised = True, published/cancelled = False
            self.assertTrue(message["finalised"])
            self.assertFalse(message["published"])
            self.assertFalse(message["cancelled"])

    def test_release_date_exists_provisional_date_absent(self):
        """If release_date is set, provisional_date should not be present."""
        page = self.release_calendar_page_confirmed
        message = self.publisher._construct_message_for_create_update(page)  # pylint: disable=W0212

        self.assert_page_message_fields(message, page)
        self.assertIsNotNone(message.get("release_date"))
        self.assertIsNone(message.get("provisional_date"))

    def test_provisional_date_exists_when_release_date_absent(self):
        """If release_date is absent, provisional_date should exist (for a provisional status)."""
        page = ReleaseCalendarPageFactory(
            status=ReleaseStatus.PROVISIONAL,
            release_date=None,
            release_date_text="Provisional release date text",
        )
        message = self.publisher._construct_message_for_create_update(page)  # pylint: disable=W0212

        self.assert_page_message_fields(message, page)
        self.assertIsNone(message.get("release_date"))
        self.assertEqual(message.get("provisional_date"), page.release_date_text)

    def test_construct_message_for_release_page_confirmed_date_change(self):
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

        message = self.publisher._construct_message_for_create_update(page)  # pylint: disable=W0212
        self.assert_page_message_fields(message, page)
        self.assert_release_page_fields(message, page)
        self.assertTrue(message["finalised"])
        self.assertFalse(message["published"])
        self.assertFalse(message["cancelled"])

        self.assert_date_changes(message, page)

    def test_construct_message_for_release_page_published(self):
        """A published release page should have release_date, published=True, finalised=False, cancelled=False."""
        page = self.release_calendar_page_published
        message = self.publisher._construct_message_for_create_update(page)  # pylint: disable=W0212

        self.assert_page_message_fields(message, page)
        self.assert_release_page_fields(message, page)
        self.assertFalse(message["finalised"])
        self.assertTrue(message["published"])
        self.assertFalse(message["cancelled"])

    def test_construct_message_for_release_page_cancelled(self):
        """A cancelled release page should have release_date, cancelled=True, finalised=False, published=False."""
        page = self.release_calendar_page_cancelled
        message = self.publisher._construct_message_for_create_update(page)  # pylint: disable=W0212

        self.assert_page_message_fields(message, page)
        self.assert_release_page_fields(message, page)
        self.assertFalse(message["finalised"])
        self.assertFalse(message["published"])
        self.assertTrue(message["cancelled"])

    def test_construct_message_for_information_page_with_topics(self):
        """Ensure that the information page message includes the correct topics."""
        page = self.info_page
        message = self.publisher._construct_message_for_create_update(page)  # pylint: disable=W0212
        self.assert_page_message_fields(message, page)

        # Confirm the topics
        self.assertEqual(message["topics"], [self.topic_a.id, self.topic_b.id])

    def test_construct_message_for_article_page_with_inherited_topics(self):
        """Ensure that the article page message contains topics inherited from the parent ArticleSeriesPage."""
        series_page = ArticleSeriesPageFactory(title="Article Series")
        GenericPageToTaxonomyTopic.objects.create(page=series_page, topic=self.topic_a)
        GenericPageToTaxonomyTopic.objects.create(page=series_page, topic=self.topic_b)

        article_page = StatisticalArticlePageFactory(
            parent=series_page, title="Statistical Article", summary="Article summary"
        )
        message = self.publisher._construct_message_for_create_update(article_page)  # pylint: disable=W0212

        self.assert_page_message_fields(message, article_page)
        self.assertEqual(message["topics"], [self.topic_a.id, self.topic_b.id])


@override_settings(
    KAFKA_SERVER="localhost:9092",
    KAFKA_CHANNEL_CREATED_OR_UPDATED="search-content-updated",
    KAFKA_CHANNEL_DELETED="search-content-deleted",
)
class KafkaPublisherTests(BasePublisherTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.information_page = InformationPageFactory()

    @patch("cms.search.publishers.KafkaProducer")
    def test_kafka_publisher_init(self, mock_producer_class):
        """Ensure KafkaPublisher picks up settings and constructs KafkaProducer correctly."""
        publisher = KafkaPublisher()
        mock_producer_class.assert_called_once_with(
            bootstrap_servers=["localhost:9092"],
            api_version=(3, 5, 1),
            value_serializer=ANY,
            retries=5,
        )
        self.assertEqual(publisher.created_or_updated_channel, "search-content-updated")
        self.assertEqual(publisher.deleted_channel, "search-content-deleted")

    @patch("cms.search.publishers.KafkaProducer")
    def test_publish_created_or_updated(self, mock_producer_class):
        """Check that publish_created_or_updated sends to Kafka with the correct channel & message."""
        mock_producer = MagicMock()
        mock_future = MagicMock()
        mock_producer.send.return_value = mock_future
        mock_producer_class.return_value = mock_producer

        publisher = KafkaPublisher()
        page = self.information_page

        result = publisher.publish_created_or_updated(page)

        # Check calls to producer
        mock_producer.send.assert_called_once()
        call_args, _ = mock_producer.send.call_args
        channel_called = call_args[0]  # "search-content-updated"
        message_called = call_args[1]  # the actual payload

        self.assertEqual(channel_called, "search-content-updated")
        self.assert_page_message_fields(message_called, page)

        mock_future.get.assert_called_once_with(timeout=10)
        self.assertEqual(result, mock_future.get.return_value)

    @patch("cms.search.publishers.KafkaProducer")
    def test_publish_deleted(self, mock_producer_class):
        """Check that publish_deleted sends to Kafka with the correct channel & message."""
        mock_producer = MagicMock()
        mock_future = MagicMock()
        mock_producer.send.return_value = mock_future
        mock_producer_class.return_value = mock_producer

        publisher = KafkaPublisher()
        page = self.information_page

        publisher.publish_deleted(page)

        mock_producer.send.assert_called_once()
        call_args, _ = mock_producer.send.call_args
        channel_called = call_args[0]  # "search-content-deleted"
        message_called = call_args[1]  # the actual payload

        self.assertEqual(channel_called, "search-content-deleted")
        self.assertIn("uri", message_called)
        self.assertEqual(message_called["uri"], page.url_path)

        mock_future.get.assert_called_once_with(timeout=10)


class LogPublisherTests(BasePublisherTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.information_page = InformationPageFactory()
        cls.publisher = LogPublisher()

    @patch.object(logging.Logger, "info")
    def test_publish_created_or_updated_logs(self, mock_logger_info):
        """Verify publish_created_or_updated logs to Logger.info with the correct arguments."""
        self.publisher.publish_created_or_updated(self.information_page)
        self.assertGreaterEqual(mock_logger_info.call_count, 1)

        last_call_args, _ = mock_logger_info.call_args
        # Format: ("LogPublisher: Publishing to channel=%s, message=%s", channel, message_dict)
        self.assertEqual(
            last_call_args[0],
            "LogPublisher: Publishing to channel=%s, message=%s",
            "Wrong log format string",
        )
        self.assertEqual(last_call_args[1], "log-created-or-updated", "Wrong channel argument")

        # The dictionary is in last_call_args[2]
        msg_dict = last_call_args[2]
        self.assert_page_message_fields(msg_dict, self.information_page)

    @patch.object(logging.Logger, "info")
    def test_publish_deleted_logs(self, mock_logger_info):
        """Verify publish_deleted logs to Logger.info with the correct arguments."""
        self.publisher.publish_deleted(self.information_page)
        self.assertGreaterEqual(mock_logger_info.call_count, 1)

        last_call_args, _ = mock_logger_info.call_args
        self.assertEqual(
            last_call_args[0],
            "LogPublisher: Publishing to channel=%s, message=%s",
            "Wrong log format string",
        )
        self.assertEqual(last_call_args[1], "log-deleted", "Wrong channel argument")

        msg_dict = last_call_args[2]
        self.assertIn("uri", msg_dict, "Payload dict missing expected key 'uri'")
        self.assertEqual(msg_dict["uri"], self.information_page.url_path)
