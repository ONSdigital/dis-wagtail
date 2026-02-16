import logging
from unittest.mock import ANY, MagicMock, patch

from django.test import TestCase, override_settings
from wagtail.test.utils import WagtailTestUtils

from cms.articles.tests.factories import StatisticalArticlePageFactory
from cms.methodology.tests.factories import MethodologyPageFactory
from cms.release_calendar.tests.factories import ReleaseCalendarPageFactory
from cms.search.publishers import BasePublisher, LogPublisher
from cms.search.publishers.kafka import IAMKafkaTokenProvider, KafkaPublisher
from cms.search.tests.helpers import ResourceDictAssertions
from cms.search.utils import build_page_uri
from cms.standard_pages.tests.factories import IndexPageFactory, InformationPageFactory
from cms.topics.tests.factories import TopicPageFactory


class DummyPublisher(BasePublisher):
    """Concrete subclass of BasePublisher for testing the shared functionality."""

    def _publish(self, channel, message):
        # We don't actually publish in tests; we just want to spy on the calls.
        pass


class BasePublisherTests(TestCase, WagtailTestUtils, ResourceDictAssertions):
    @classmethod
    def setUpTestData(cls):
        cls.superuser = cls.create_superuser(username="admin")
        # Pages included in the search index, as they are not in SEARCH_INDEX_EXCLUDED_PAGE_TYPES
        cls.included_pages = [
            InformationPageFactory(),
            MethodologyPageFactory(),
            ReleaseCalendarPageFactory(),
            StatisticalArticlePageFactory(),
            StatisticalArticlePageFactory(news_headline=""),
            IndexPageFactory(slug="custom-slug-1"),
            TopicPageFactory(),
        ]

        cls.publisher = DummyPublisher()

    @patch.object(DummyPublisher, "_publish", return_value=None)
    def test_publish_created_or_updated_calls_publish(self, mock_method):
        """Verify `publish_created_or_updated` calls `_publish` with correct channel & message."""
        for page in self.included_pages:
            self.publisher.publish_created_or_updated(page)

            # The channel should come from created_or_updated_channel
            mock_method.assert_called_once()
            channel_called, message_called = mock_method.call_args[0]

            self.assertEqual(channel_called, "search-content-updated")
            title = page.get_full_display_title() if type(page).__name__ == "StatisticalArticlePage" else page.title
            self.assert_base_fields(message_called, page, title=title)

            mock_method.reset_mock()

    @patch.object(DummyPublisher, "_publish", return_value=None)
    def test_publish_deleted_calls_publish(self, mock_method):
        """Verify `publish_deleted` calls `_publish` with the correct channel & message."""
        for page in self.included_pages:
            self.publisher.publish_deleted(page)

            mock_method.assert_called_once()
            channel_called, message_called = mock_method.call_args[0]

            self.assertEqual(channel_called, "search-content-deleted")
            self.assertIn("uri", message_called)
            self.assertEqual(message_called["uri"], build_page_uri(page))

            mock_method.reset_mock()


@override_settings(
    KAFKA_SERVERS=["localhost:9092"],
)
class KafkaPublisherTests(TestCase, ResourceDictAssertions):
    @classmethod
    def setUpTestData(cls):
        cls.information_page = InformationPageFactory()

    @patch("cms.search.publishers.KafkaProducer")
    def test_kafka_publisher_init(self, mock_producer_class):
        """Ensure KafkaPublisher picks up settings and constructs KafkaProducer correctly."""
        KafkaPublisher()
        mock_producer_class.assert_called_once_with(
            bootstrap_servers=["localhost:9092"],
            api_version_auto_timeout_ms=5000,
            value_serializer=ANY,
            retries=5,
        )

    @patch("cms.search.publishers.KafkaProducer")
    def test_publish_created_or_updated(self, mock_producer_class):
        """Check that publish_created_or_updated sends to Kafka with the correct channel & message."""
        mock_producer = MagicMock()
        mock_future = MagicMock()
        mock_producer.send.return_value = mock_future
        mock_producer_class.return_value = mock_producer

        publisher = KafkaPublisher()
        page = self.information_page

        publisher.publish_created_or_updated(page)

        # Check calls to producer
        mock_producer.send.assert_called_once()
        call_args, _ = mock_producer.send.call_args
        channel_called = call_args[0]  # "search-content-updated"
        message_called = call_args[1]  # the actual payload

        self.assertEqual(channel_called, "search-content-updated")
        self.assert_base_fields(message_called, page)

        mock_future.get.assert_called_once_with(timeout=10)

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
        self.assertEqual(message_called["uri"], build_page_uri(page))

        mock_future.get.assert_called_once_with(timeout=10)

    def test_token_provider_cache_key(self):
        token_provider = IAMKafkaTokenProvider()
        self.assertEqual(
            token_provider.token.get_cache_key(token_provider), "cms.search.publishers.IAMKafkaTokenProvider"
        )

    @patch("cms.search.publishers.MSKAuthTokenProvider.generate_auth_token")
    def test_token_provider(self, mock_generate_auth_token):
        mock_generate_auth_token.return_value = ("msk-token", None)
        token_provider = IAMKafkaTokenProvider()

        self.assertEqual(token_provider.token(), "msk-token")
        self.assertEqual(token_provider.token(), "msk-token")

        mock_generate_auth_token.assert_called_once()


class LogPublisherTests(TestCase, ResourceDictAssertions):
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
        self.assertEqual(
            last_call_args[0],
            "LogPublisher: Publishing to channel=%s, message=%s",
            "Wrong log format string",
        )
        self.assertEqual(last_call_args[1], "search-content-updated", "Wrong channel argument")

        msg_dict = last_call_args[2]
        self.assert_base_fields(msg_dict, self.information_page)

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
        self.assertEqual(last_call_args[1], "search-content-deleted", "Wrong channel argument")

        msg_dict = last_call_args[2]
        self.assertIn("uri", msg_dict, "Payload dict missing expected key 'uri'")
        self.assertEqual(msg_dict["uri"], build_page_uri(self.information_page))
