# test_publishers.py
from django.test import TestCase, override_settings
from unittest.mock import patch, MagicMock
import logging

from cms.search.publishers import BasePublisher, KafkaPublisher, LogPublisher

from cms.articles.tests.factories import StatisticalArticlePageFactory
from cms.methodology.tests.factories import MethodologyPageFactory
from cms.release_calendar.tests.factories import ReleaseCalendarPageFactory
from cms.standard_pages.tests.factories import IndexPageFactory, InformationPageFactory
from cms.release_calendar.enums import ReleaseStatus
from django.utils import timezone
from datetime import timedelta


class DummyPublisher(BasePublisher):
    """Concrete subclass of BasePublisher for testing the shared functionality."""

    def __init__(self, topic_created_or_updated, topic_deleted):
        self._topic_created_or_updated = topic_created_or_updated
        self._topic_deleted = topic_deleted

    def _publish_to_service(self, topic, message):
        # We don't actually publish in tests; we just want to spy on the calls.
        pass

    def get_topic_created_or_updated(self):
        return self._topic_created_or_updated

    def get_topic_deleted(self):
        return self._topic_deleted


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
            topic_created_or_updated="dummy-topic-created",
            topic_deleted="dummy-topic-deleted",
        )

    def test_publish_created_or_updated_calls_publish_to_service(self):
        """Verify `publish_created_or_updated` calls `_publish_to_service` with the correct topic & message."""
        with patch.object(self.publisher, "_publish_to_service", return_value=None) as mock_method:
            for factory in self.included_factories:
                page = factory()

                self.publisher.publish_created_or_updated(page)

                # The topic should come from get_topic_created_or_updated()
                mock_method.assert_called_once()
                called_topic, called_message = mock_method.call_args[0]
                self.assertEqual(called_topic, "dummy-topic-created")

                # Check the message structure from _construct_message_for_create_update
                self.assertIn("uri", called_message)
                self.assertIn("title", called_message)
                self.assertIn("content_type", called_message)
                self.assertIn("summary", called_message)
                self.assertIn("topics", called_message)

                self.assertEqual(called_message["uri"], page.url_path)
                self.assertEqual(called_message["title"], page.title)
                self.assertEqual(called_message["summary"], page.summary)
                self.assertEqual(called_message["content_type"], page.content_type_id)

                mock_method.reset_mock()
                # Not a release => no date

    def test_publish_deleted_calls_publish_to_service(self):
        """Verify `publish_deleted` calls `_publish_to_service` with the correct topic & message."""
        with patch.object(self.publisher, "_publish_to_service", return_value=None) as mock_method:
            for factory in self.included_factories:
                page = factory()
                self.publisher.publish_deleted(page)

                mock_method.assert_called_once()
                called_topic, called_message = mock_method.call_args[0]
                self.assertEqual(called_topic, "dummy-topic-deleted")

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
            message = self.publisher._construct_message_for_create_update(page)

            self.assertEqual(message["content_type"], page.content_type_id)
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

        message = self.publisher._construct_message_for_create_update(page)

        self.assertEqual(message["content_type"], page.content_type_id)
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

        message = self.publisher._construct_message_for_create_update(page)

        self.assertEqual(message["content_type"], page.content_type_id)
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

        message = self.publisher._construct_message_for_create_update(page)

        self.assertEqual(message["content_type"], page.content_type_id)
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
    KAFKA_TOPIC_CREATED_OR_UPDATED="search-content-updated",
    KAFKA_TOPIC_DELETED="search-content-deleted",
)
class KafkaPublisherTests(TestCase):
    @patch("cms.search.publishers.KafkaProducer")
    def test_kafka_publisher_init(self, mock_producer_class):
        """Ensure KafkaPublisher picks up settings and constructs KafkaProducer correctly."""
        publisher = KafkaPublisher()
        mock_producer_class.assert_called_once_with(
            bootstrap_servers=["localhost:9092"],
            api_version=(3, 8, 0),
            value_serializer=publisher.producer._serializer,  # or a lambda
        )
        self.assertEqual(publisher._topic_created_or_updated, "search-content-updated")
        self.assertEqual(publisher._topic_deleted, "search-content-deleted")

    @patch("cms.search.publishers.KafkaProducer")
    def test_publish_created_or_updated(self, mock_producer_class):
        """Check that publish_created_or_updated sends to Kafka with the correct topic & message."""
        mock_producer = MagicMock()
        mock_future = MagicMock()
        mock_producer.send.return_value = mock_future
        mock_producer_class.return_value = mock_producer

        publisher = KafkaPublisher()

        # Mock page
        page = MagicMock()
        page.url_path = "/mock-page/"
        page.title = "Mock Title"
        page.summary = "Mock Summary"
        page.__class__.__name__ = "InformationPage"
        page.content_type_id = 999

        result = publisher.publish_created_or_updated(page)

        # Check calls to producer
        mock_producer.send.assert_called_once()
        call_args, call_kwargs = mock_producer.send.call_args
        self.assertEqual(call_args[0], "search-content-updated")  # topic
        # The actual payload is the second argument
        actual_payload = call_args[1]
        self.assertIn("uri", actual_payload)
        self.assertIn("title", actual_payload)
        self.assertEqual(actual_payload["uri"], "/mock-page/")
        self.assertEqual(actual_payload["title"], "Mock Title")
        self.assertEqual(actual_payload["content_type"], 999)

        # Future get called?
        mock_future.get.assert_called_once_with(timeout=10)

        # The publisher returns the result of future.get()
        self.assertEqual(result, mock_future.get.return_value)

    @patch("cms.search.publishers.KafkaProducer")
    def test_publish_deleted(self, mock_producer_class):
        """Check that publish_deleted sends to Kafka with the correct topic & message."""
        mock_producer = MagicMock()
        mock_future = MagicMock()
        mock_producer.send.return_value = mock_future
        mock_producer_class.return_value = mock_producer

        publisher = KafkaPublisher()

        page = MagicMock()
        page.url_path = "/delete-me/"
        page.trace_id = "TRACE-123"

        publisher.publish_deleted(page)

        mock_producer.send.assert_called_once()
        call_args, call_kwargs = mock_producer.send.call_args
        self.assertEqual(call_args[0], "search-content-deleted")  # topic
        actual_payload = call_args[1]
        self.assertIn("uri", actual_payload)
        self.assertEqual(actual_payload["uri"], "/delete-me/")
        self.assertEqual(actual_payload["trace_id"], "TRACE-123")

        # confirm get() is called
        mock_future.get.assert_called_once_with(timeout=10)


class LogPublisherTests(TestCase):
    def setUp(self):
        self.publisher = LogPublisher()

    @patch.object(logging.Logger, "info")
    def test_publish_created_or_updated_logs(self, mock_logger_info):
        page = MagicMock()
        page.url_path = "/logging-page/"
        page.title = "Log Me"
        page.summary = "some text"
        page.__class__.__name__ = "StatisticalArticlePage"
        page.content_type_id = 1234

        self.publisher.publish_created_or_updated(page)

        # We expect two logs:
        # 1) "BasePublisher: About to publish created/updated message=..."
        # 2) "LogPublisher: topic=%s message=%s"
        self.assertGreaterEqual(mock_logger_info.call_count, 2)

        # The last call is the LogPublisher info
        last_call_args, last_call_kwargs = mock_logger_info.call_args
        self.assertIn("LogPublisher: topic=log-created-or-updated message=", last_call_args[0])

    @patch.object(logging.Logger, "info")
    def test_publish_deleted_logs(self, mock_logger_info):
        page = MagicMock()
        page.url_path = "/delete-logging/"
        page.trace_id = "XYZ-999"

        self.publisher.publish_deleted(page)
        self.assertGreaterEqual(mock_logger_info.call_count, 2)

        last_call_args, last_call_kwargs = mock_logger_info.call_args
        self.assertIn("LogPublisher: topic=log-deleted message=", last_call_args[0])
