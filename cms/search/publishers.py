from abc import ABC, abstractmethod
import os
import json
from kafka import KafkaProducer
import logging
from django.conf import settings


class BasePublisher(ABC):
    @abstractmethod
    def publish_created_or_updated(self, page):
        pass

    @abstractmethod
    def publish_deleted(self, page):
        pass


class KafkaPublisher(BasePublisher):
    def __init__(self):
        # Read Kafka configs from environment or settings
        # self.kafka_server = os.getenv("KAFKA_SERVER", "localhost:9092")
        # self.topic_created_or_updated = os.getenv("KAFKA_TOPIC_CREATED_OR_UPDATED", "search-content-updated")
        # self.topic_deleted = os.getenv("KAFKA_TOPIC_DELETED", "search-content-deleted")

        self.kafka_server = getattr(settings, "KAFKA_SERVER", "localhost:9092")
        self.topic_created_or_updated = getattr(settings, "KAFKA_TOPIC_CREATED_OR_UPDATED", "search-content-updated")
        self.topic_deleted = getattr(settings, "KAFKA_TOPIC_DELETED", "search-content-deleted")

        self.producer = KafkaProducer(
            bootstrap_servers=[self.kafka_server],
            api_version=(3, 8, 0),
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
        )

    def publish_created_or_updated(self, page):
        message = self._construct_message_for_create_update(page)
        self.producer.send(self.topic_created_or_updated, message)
        self.producer.flush()

    def publish_deleted(self, page):
        message = self._construct_message_for_delete(page)
        self.producer.send(self.topic_deleted, message)
        self.producer.flush()

    def _construct_message_for_create_update(self, page):
        """Build a dict that matches the agreed metadata schema for 'created/updated'.
        Example fields below; tailor them to your search metadata specs.
        """
        return {
            "title": page.title,
            "id": page.id,
            "url": page.full_url if hasattr(page, "full_url") else None,
            "last_published_at": page.last_published_at.isoformat() if page.last_published_at else None,
            "data_type": self._map_page_type_to_data_type(page),
            # ... more fields as needed
        }

    def _construct_message_for_delete(self, page):
        """Build a dict that matches the agreed metadata schema for 'deleted' events."""
        return {
            "id": page.id,
            "title": page.title,
            "deleted_at": page.last_published_at.isoformat() if page.last_published_at else None,
            # ... more fields as needed
        }

    def _map_page_type_to_data_type(self, page):
        """Map Wagtail Page subclass to the data type required. For example:
        - If it's a Statistical Article page, return 'bulletin'
        - Otherwise, return something else (like page.specific_class or a default).
        """
        # Example logic:
        if page.__class__.__name__ == "StatisticalArticlePage":
            return "bulletin"
        return "generic"


class LogPublisher(BasePublisher):
    def publish_created_or_updated(self, page):
        logging.info("Created/Updated event for page ID %s", page.id)

    def publish_deleted(self, page):
        logging.info("Deleted event for page ID %s", page.id)


class NullPublisher(BasePublisher):
    def publish_created_or_updated(self, page):
        pass

    def publish_deleted(self, page):
        pass
