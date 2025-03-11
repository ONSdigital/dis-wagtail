from abc import ABC, abstractmethod
import os
import json
from kafka import KafkaProducer
import logging
from django.conf import settings

logger = logging.getLogger(__name__)


class BasePublisher(ABC):
    @abstractmethod
    def publish_created_or_updated(self, page):
        pass

    @abstractmethod
    def publish_deleted(self, page):
        pass


class KafkaPublisher(BasePublisher):
    """Publishes messages to Kafka for 'search-content-updated' (created or updated)
    and 'search-content-deleted' (deleted) events, aligning with the StandardPayload / ReleasePayload / content-deleted schema definitions.
    """

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
        """Build and publish a message to the search-content-updated topic.
        The message will be either:
          - StandardPayload, if content_type != "release"
          - ReleasePayload, if content_type == "release".
        """
        message = self._construct_message_for_create_update(page)
        logger.info("Publishing CREATED/UPDATED to topic=%s, message=%s", self.topic_created_or_updated, message)

        future = self.producer.send(self.topic_created_or_updated, message)
        # Optionally block for the result, capturing metadata or error
        result = future.get(timeout=10)  # Wait up to 10s for send to complete
        logger.info("Publish result for topic %s: %s", self.topic_created_or_updated, result)

    def publish_deleted(self, page):
        """Build and publish a 'content-deleted' message to Kafka,
        matching the content-deleted schema (requires only 'uri').
        """
        message = self._construct_message_for_delete(page)
        logger.info("Publishing DELETED to topic=%s, message=%s", self.topic_deleted, message)

        future = self.producer.send(self.topic_deleted, message)
        result = future.get(timeout=10)
        logger.info("Publish result for topic %s: %s", self.topic_deleted, result)

    def _construct_message_for_create_update(self, page):
        """Build a dict that matches the agreed metadata schema for 'created/updated'.

        resource_metadata.yml:
           - StandardPayload: requires {uri, title, content_type}, optional fields
           - ReleasePayload: extends StandardPayload with release-specific fields
        """
        # For pages that are 'release' content, we add release fields below.
        content_type = self._map_page_type_to_content_type(page)
        # breakpoint()

        # Common fields for StandardPayload (also part of ReleasePayload)
        # The schema requires at minimum: uri, title, content_type
        message = {
            "uri": page.url_path,
            "uri_old": "",  # optional, if needed
            "content_type": page.content_type_id,
            "cdid": getattr(page, "cdid", None),
            "dataset_id": getattr(page, "dataset_id", None),
            "edition": getattr(page, "edition", None),
            "meta_description": getattr(page, "meta_description", None),
            # if page.release_date is a datetime, convert to isoformat
            "release_date": (
                page.release_date.isoformat() if hasattr(page, "release_date") and page.release_date else None
            ),
            "summary": getattr(page, "summary", None),
            "title": page.title,
            "topics": list(page.topics.values_list("topic_id", flat=True)),
            "language": getattr(page, "language", None),
            "survey": getattr(page, "survey", None),
            "canonical_topic": getattr(page, "canonical_topic", None),
        }

        # If it's a Release, we add the extra fields from ReleasePayload
        if content_type == "release":
            breakpoint()
            message["cancelled"] = getattr(page, "cancelled", False)
            message["finalised"] = getattr(page, "finalised", False)
            message["published"] = getattr(page, "published", False)
            message["date_changes"] = getattr(page, "date_changes", [])
            message["provisional_date"] = getattr(page, "provisional_date", "")

        return message

    def _construct_message_for_delete(self, page):
        """Build a dict that matches the 'content-deleted' schema:
          - required: uri
          - optional: trace_id
        We'll use page.full_url or fallback for 'uri'.
        """
        message = {
            "uri": page.url_path,
        }

        if hasattr(page, "trace_id") and page.trace_id:
            message["trace_id"] = page.trace_id

        return message

    def _map_page_type_to_content_type(self, page):
        """Map Wagtail Page subclasses to your enumerated content_type for the schema.
        The schema enumerates possibilities like 'release', 'bulletin', 'article', etc.
        """
        page_class_name = page.__class__.__name__

        if page_class_name == "ReleaseCalendarPage":
            return "release"
        elif page_class_name == "StatisticalArticlePage":
            return "bulletin"
        else:
            # Example JSON used "standard" or "release".
            # Official enum doesn't have "standard"
            return "standard"


class LogPublisher(BasePublisher):
    def publish_created_or_updated(self, page):
        logger.info("Created/Updated event for page ID %s", page.id)

    def publish_deleted(self, page):
        logger.info("Deleted event for page ID %s", page.id)


class NullPublisher(BasePublisher):
    def publish_created_or_updated(self, page):
        pass

    def publish_deleted(self, page):
        pass
