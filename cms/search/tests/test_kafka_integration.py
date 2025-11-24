import json
import logging
import time

from django.conf import settings
from django.test import TestCase
from kafka import KafkaConsumer

from cms.search.publishers import KafkaPublisher
from cms.search.utils import build_page_uri
from cms.standard_pages.tests.factories import InformationPageFactory


class KafkaIntegrationTests(TestCase):
    """These tests will attempt to connect to a real Kafka instance at localhost:9092."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Create a KafkaConsumer to listen to the same topics
        # so we can verify messages that come in.
        cls.consumer_created = KafkaConsumer(
            "search-content-updated",
            bootstrap_servers=settings.KAFKA_SERVERS,
            auto_offset_reset="earliest",
            enable_auto_commit=True,
            group_id="test-group-created-updated",
        )

        cls.consumer_deleted = KafkaConsumer(
            "search-content-deleted",
            bootstrap_servers=settings.KAFKA_SERVERS,
            auto_offset_reset="earliest",
            enable_auto_commit=True,
            group_id="test-group-deleted",
        )

        cls.publisher = KafkaPublisher()
        logging.getLogger(__name__).info("KafkaIntegrationTests: setUpClass complete.")

    @classmethod
    def tearDownClass(cls):
        # Close the consumers
        cls.consumer_created.close()
        cls.consumer_deleted.close()
        super().tearDownClass()

    def _poll_for_message(self, consumer, expected_uri, timeout_seconds=5):
        """Polls the given consumer for up to `timeout_seconds` seconds,
        returning True if a message with the given `expected_uri` is found.
        """
        start_time = time.time()
        while time.time() - start_time < timeout_seconds:
            raw_msgs = consumer.poll(timeout_ms=1000)
            for _tp, msgs in raw_msgs.items():
                for msg in msgs:
                    payload = json.loads(msg.value.decode("utf-8"))
                    if payload.get("uri") == expected_uri:
                        return True
        return False

    def test_publish_created_or_updated_integration(self):
        """Publish a "created/updated" message to Kafka and consume it,
        verifying that the message is indeed in the channel.
        """
        page = InformationPageFactory()
        publish_result = self.publisher.publish_created_or_updated(page)
        self.assertIsNotNone(publish_result)  # We get some metadata from Kafka

        msg_found = self._poll_for_message(self.consumer_created, build_page_uri(page))
        self.assertTrue(msg_found, "No matching message found in 'search-content-updated' channel.")

    def test_publish_deleted_integration(self):
        """Publish a "deleted" message to Kafka and consume it from 'search-content-deleted'."""
        page = InformationPageFactory()

        self.publisher.publish_deleted(page)

        msg_found = self._poll_for_message(self.consumer_deleted, build_page_uri(page))
        self.assertTrue(msg_found, "No matching message found in 'search-content-deleted' channel.")
