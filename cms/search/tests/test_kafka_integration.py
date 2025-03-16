# test_kafka_integration.py
import json
import time
import logging
from django.test import TestCase, override_settings
from kafka import KafkaConsumer

from cms.search.publishers import KafkaPublisher
from cms.standard_pages.tests.factories import InformationPageFactory


@override_settings(
    KAFKA_SERVER="localhost:9092",
    KAFKA_TOPIC_CREATED_OR_UPDATED="search-content-updated",
    KAFKA_TOPIC_DELETED="search-content-deleted",
)
class KafkaIntegrationTests(TestCase):
    """These tests will attempt to connect to a real Kafka instance at localhost:9092."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Create a KafkaConsumer to listen to the same topics
        # so we can verify messages that come in.
        cls.consumer_created = KafkaConsumer(
            "search-content-updated",
            bootstrap_servers=["localhost:9092"],
            auto_offset_reset="earliest",
            enable_auto_commit=True,
            group_id="test-group-created-updated",
        )

        cls.consumer_deleted = KafkaConsumer(
            "search-content-deleted",
            bootstrap_servers=["localhost:9092"],
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

    def test_publish_created_or_updated_integration(self):
        """Publish a "created/updated" message to Kafka and consume it,
        verifying that the message is indeed in the topic.
        """
        # 1) Publish a test message
        page = InformationPageFactory()
        publish_result = self.publisher.publish_created_or_updated(page)
        self.assertIsNotNone(publish_result)  # We get some metadata from Kafka

        # 2) Attempt to consume the message
        # We'll poll for a limited time to see if we can read a new message off 'search-content-updated'.
        msg_found = False
        start_time = time.time()
        while time.time() - start_time < 5:  # up to 5 seconds
            raw_msgs = self.consumer_created.poll(timeout_ms=1000)
            for tp, msgs in raw_msgs.items():
                for msg in msgs:
                    payload = json.loads(msg.value.decode("utf-8"))
                    if payload.get("uri") == page.url_path:
                        msg_found = True
                        break
                if msg_found:
                    break
            if msg_found:
                break

        self.assertTrue(msg_found, "No matching message found in 'search-content-updated' topic.")

    def test_publish_deleted_integration(self):
        """Publish a "deleted" message to Kafka and consume it from 'search-content-deleted'."""
        page = InformationPageFactory()

        _ = self.publisher.publish_deleted(page)

        msg_found = False
        start_time = time.time()
        while time.time() - start_time < 5:  # up to 5 seconds
            raw_msgs = self.consumer_deleted.poll(timeout_ms=1000)
            for tp, msgs in raw_msgs.items():
                for msg in msgs:
                    payload = json.loads(msg.value.decode("utf-8"))
                    if payload.get("uri") == page.url_path:
                        msg_found = True
                        break
                if msg_found:
                    break
            if msg_found:
                break

        self.assertTrue(msg_found, "No matching message found in 'search-content-deleted' topic.")
