# test_publishers.py
import logging
from datetime import timedelta
from unittest.mock import ANY, MagicMock, patch

from django.test import TestCase, override_settings
from django.utils import timezone

from cms.articles.tests.factories import StatisticalArticlePageFactory
from cms.methodology.tests.factories import MethodologyPageFactory
from cms.release_calendar.enums import ReleaseStatus
from cms.release_calendar.tests.factories import ReleaseCalendarPageFactory
from cms.search.publishers import BasePublisher, KafkaPublisher, LogPublisher
from cms.standard_pages.tests.factories import IndexPageFactory, InformationPageFactory

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

    def _publish(self, channel, message):
        # We don't actually publish in tests; we just want to spy on the calls.
        pass

    def get_created_or_updated_channel(self):
        return self._channel_created_or_updated

    def get_deleted_channel(self):
        return self._channel_deleted


class BasePublisherTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.included_factories = [
            InformationPageFactory,
            MethodologyPageFactory,
            ReleaseCalendarPageFactory,
            StatisticalArticlePageFactory,
        ]

        cls.index_page = IndexPageFactory(slug="custom-slug-1")
        cls.included_factories.append(lambda: cls.index_page)

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

    def setUp(self):
        self.publisher = DummyPublisher(
            channel_created_or_updated="dummy-channel-created",
            channel_deleted="dummy-channel-deleted",
        )

    def test_publish_created_or_updated_calls_publish(self):
        """Verify `publish_created_or_updated` calls `_publish` with the correct channel & message."""
        with patch.object(self.publisher, "_publish", return_value=None) as mock_method:
            for factory in self.included_factories:
                page = factory()

                self.publisher.publish_created_or_updated(page)
                expected_type = EXPECTED_CONTENT_TYPES[type(page).__name__]

                # The channel should come from get_channel_created_or_updated()
                mock_method.assert_called_once()
                called_channel, called_message = mock_method.call_args[0]
                self.assertEqual(called_channel, "dummy-channel-created")

                # Check the message structure from _construct_message_for_create_update
                self.assertIn("uri", called_message)
                self.assertIn("title", called_message)
                self.assertIn("content_type", called_message)
                self.assertIn("summary", called_message)
                self.assertIn("topics", called_message)

                self.assertEqual(called_message["uri"], page.url_path)
                self.assertEqual(called_message["title"], page.title)
                self.assertEqual(called_message["summary"], page.summary)
                self.assertEqual(called_message["content_type"], expected_type)

                mock_method.reset_mock()
                # Not a release => no date

    def test_publish_deleted_calls_publish(self):
        """Verify `publish_deleted` calls `_publish` with the correct channel & message."""
        with patch.object(self.publisher, "_publish", return_value=None) as mock_method:
            for factory in self.included_factories:
                page = factory()
                self.publisher.publish_deleted(page)

                mock_method.assert_called_once()
                called_channel, called_message = mock_method.call_args[0]
                self.assertEqual(called_channel, "dummy-channel-deleted")

                self.assertIn("uri", called_message)

                self.assertEqual(called_message["uri"], page.url_path)

                mock_method.reset_mock()

    def test_construct_message_for_release_page_provisional_confirmed(self):
        """Ensure that for a release-type page, release-specific fields get added."""
        release_calendar_pages = [
            self.release_calendar_page_provisional,
            self.release_calendar_page_confirmed,
        ]

        for page in release_calendar_pages:
            message = self.publisher._construct_message_for_create_update(page)  # pylint: disable=W0212
            expected_type = EXPECTED_CONTENT_TYPES[type(page).__name__]

            self.assertEqual(message["content_type"], expected_type)
            self.assertEqual(message["title"], page.title)
            self.assertEqual(message["summary"], page.summary)
            self.assertEqual(message["uri"], page.url_path)

            self.assertIsNotNone(message["release_date"])  # because it's a release

            self.assertEqual(message["release_date"], page.release_date.isoformat().replace("+00:00", "Z"))

            self.assertIn("finalised", message)
            self.assertIn("cancelled", message)
            self.assertIn("published", message)

            self.assertTrue(message["finalised"])
            self.assertFalse(message["published"])
            self.assertFalse(message["cancelled"])

    def test_construct_message_for_release_page_confirmed_date_change(self):
        """Ensure that for a release-type page, release-specific fields get added."""
        page = self.release_calendar_page_confirmed
        page.changes_to_release_date = [
            {
                "type": "date_change_log",
                "value": {"previous_date": timezone.now() - timedelta(days=5), "reason_for_change": "The reason"},
            }
        ]

        message = self.publisher._construct_message_for_create_update(page)  # pylint: disable=W0212
        expected_type = EXPECTED_CONTENT_TYPES[type(page).__name__]

        self.assertEqual(message["content_type"], expected_type)
        self.assertEqual(message["title"], page.title)
        self.assertEqual(message["summary"], page.summary)
        self.assertEqual(message["uri"], page.url_path)

        self.assertIsNotNone(message["release_date"])  # because it's a release

        self.assertEqual(message["release_date"], page.release_date.isoformat().replace("+00:00", "Z"))

        self.assertIn("finalised", message)
        self.assertIn("cancelled", message)
        self.assertIn("published", message)

        self.assertTrue(message["finalised"])
        self.assertFalse(message["published"])
        self.assertFalse(message["cancelled"])

        self.assertIn("date_changes", message)

        self.assertEqual(len(message["date_changes"]), 1)

        date_change = message["date_changes"][0]
        self.assertEqual(date_change["change_notice"], page.changes_to_release_date[0].value["reason_for_change"])
        self.assertEqual(
            date_change["previous_date"],
            page.changes_to_release_date[0].value["previous_date"].isoformat().replace("+00:00", "Z"),
        )

    def test_construct_message_for_release_page_published(self):
        """Ensure that for a release-type page, release-specific fields get added."""
        page = self.release_calendar_page_published

        message = self.publisher._construct_message_for_create_update(page)  # pylint: disable=W0212
        expected_type = EXPECTED_CONTENT_TYPES[type(page).__name__]

        self.assertEqual(message["content_type"], expected_type)
        self.assertEqual(message["title"], page.title)
        self.assertEqual(message["summary"], page.summary)
        self.assertEqual(message["uri"], page.url_path)

        self.assertIsNotNone(message["release_date"])  # because it's a release

        self.assertEqual(message["release_date"], page.release_date.isoformat().replace("+00:00", "Z"))

        self.assertIn("finalised", message)
        self.assertIn("cancelled", message)
        self.assertIn("published", message)

        self.assertFalse(message["finalised"])
        self.assertTrue(message["published"])
        self.assertFalse(message["cancelled"])

    def test_construct_message_for_release_page_cancelled(self):
        """Ensure that for a release-type page, release-specific fields get added."""
        page = self.release_calendar_page_cancelled

        message = self.publisher._construct_message_for_create_update(page)  # pylint: disable=W0212
        expected_type = EXPECTED_CONTENT_TYPES[type(page).__name__]

        self.assertEqual(message["content_type"], expected_type)
        self.assertEqual(message["title"], page.title)
        self.assertEqual(message["summary"], page.summary)
        self.assertEqual(message["uri"], page.url_path)

        self.assertIsNotNone(message["release_date"])  # because it's a release

        self.assertEqual(message["release_date"], page.release_date.isoformat().replace("+00:00", "Z"))

        self.assertIn("finalised", message)
        self.assertIn("cancelled", message)
        self.assertIn("published", message)

        self.assertFalse(message["finalised"])
        self.assertFalse(message["published"])
        self.assertTrue(message["cancelled"])


@override_settings(
    KAFKA_SERVER="localhost:9092",
    KAFKA_CHANNEL_CREATED_OR_UPDATED="search-content-updated",
    KAFKA_CHANNEL_DELETED="search-content-deleted",
)
class KafkaPublisherTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.information_page = InformationPageFactory()

    @patch("cms.search.publishers.KafkaProducer")
    def test_kafka_publisher_init(self, mock_producer_class):
        """Ensure KafkaPublisher picks up settings and constructs KafkaProducer correctly."""
        publisher = KafkaPublisher()
        mock_producer_class.assert_called_once_with(
            bootstrap_servers=["localhost:9092"],
            api_version=(3, 8, 0),
            value_serializer=ANY,  # or a lambda
        )

        self.assertEqual(publisher._channel_created_or_updated, "search-content-updated")  # pylint: disable=W0212
        self.assertEqual(publisher._channel_deleted, "search-content-deleted")  # pylint: disable=W0212

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
        expected_type = EXPECTED_CONTENT_TYPES[type(page).__name__]

        # Check calls to producer
        mock_producer.send.assert_called_once()
        call_args, call_kwargs = mock_producer.send.call_args  # pylint: disable=W0612
        self.assertEqual(call_args[0], "search-content-updated")  # channel
        # The actual payload is the second argument
        actual_payload = call_args[1]

        self.assertIn("uri", actual_payload)
        self.assertIn("title", actual_payload)
        self.assertIn("summary", actual_payload)
        self.assertIn("content_type", actual_payload)

        self.assertEqual(actual_payload["uri"], page.url_path)
        self.assertEqual(actual_payload["title"], page.title)
        self.assertEqual(actual_payload["summary"], page.summary)
        self.assertEqual(actual_payload["content_type"], expected_type)

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
        call_args, call_kwargs = mock_producer.send.call_args  # pylint: disable=W0612
        self.assertEqual(call_args[0], "search-content-deleted")  # channel
        actual_payload = call_args[1]

        self.assertIn("uri", actual_payload)

        self.assertEqual(actual_payload["uri"], page.url_path)

        # confirm get() is called
        mock_future.get.assert_called_once_with(timeout=10)


class LogPublisherTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.information_page = InformationPageFactory()

    def setUp(self):
        self.publisher = LogPublisher()

    @patch.object(logging.Logger, "info")
    def test_publish_created_or_updated_logs(self, mock_logger_info):
        self.publisher.publish_created_or_updated(self.information_page)

        # Make sure there was at least one info log call
        self.assertGreaterEqual(mock_logger_info.call_count, 1)

        # Examine the last call
        last_call_args, last_call_kwargs = mock_logger_info.call_args  # pylint: disable=W0612

        # The format string is arg 0, the next args are "log-created-or-updated" and the dict
        self.assertEqual(
            last_call_args[0],
            "LogPublisher: channel=%s message=%s",
            "Wrong log format string",
        )
        self.assertEqual(
            last_call_args[1],
            "log-created-or-updated",
            "Wrong channel argument",
        )

        self.assertIn("uri", last_call_args[2], "Payload dict missing expected key 'uri'")
        self.assertIn("title", last_call_args[2], "Payload dict missing expected key 'title'")
        self.assertIn("summary", last_call_args[2], "Payload dict missing expected key 'summary'")
        self.assertIn("content_type", last_call_args[2], "Payload dict missing expected key 'content_type'")
        self.assertIn("topics", last_call_args[2], "Payload dict missing expected key 'topics'")
        self.assertIn("release_date", last_call_args[2], "Payload dict missing expected key 'topics'")

    @patch.object(logging.Logger, "info")
    def test_publish_deleted_logs(self, mock_logger_info):
        self.publisher.publish_deleted(self.information_page)
        self.assertGreaterEqual(mock_logger_info.call_count, 2)

        last_call_args, last_call_kwargs = mock_logger_info.call_args  # pylint: disable=W0612

        self.assertEqual(
            last_call_args[0],
            "LogPublisher: channel=%s message=%s",
            "Wrong log format string",
        )
        self.assertEqual(
            last_call_args[1],
            "log-deleted",
            "Wrong channel argument",
        )

        self.assertIn("uri", last_call_args[2], "Payload dict missing expected key 'uri'")
