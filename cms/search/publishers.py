from abc import ABC, abstractmethod
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
        # Read Kafka configs settings
        self.kafka_server = settings.KAFKA_SERVER
        self.topic_created_or_updated = settings.KAFKA_TOPIC_CREATED_OR_UPDATED
        self.topic_deleted = settings.KAFKA_TOPIC_DELETED

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

        # Common fields for StandardPayload (also part of ReleasePayload)
        # The schema requires at minimum: uri, title, content_type
        message = {
            "uri": page.url_path,
            "content_type": page.content_type_id,
            "release_date": page.release_date.isoformat().replace("+00:00", "Z") if content_type == "release" else None,
            "summary": page.summary,
            "title": page.title,
            "topics": list(page.topics.values_list("topic_id", flat=True)),
        }

        # If it's a Release, we add the extra fields from ReleasePayload
        if content_type == "release":
            message.update(self._construct_release_specific_fields(page))
        return message

    def _construct_release_specific_fields(self, page):
        """Constructs and returns a dictionary with release-specific fields."""
        release_fields = {
            "finalised": page.status in ["CONFIRMED", "PROVISIONAL"],
            "cancelled": page.status == "CANCELLED",
            "published": page.status == "PUBLISHED",
            "date_changes": [
                {
                    "change_notice": page.changes_to_release_date[0].value["reason_for_change"],
                    "previous_date": page.changes_to_release_date[0]
                    .value["previous_date"]
                    .isoformat()
                    .replace("+00:00", "Z"),
                }
            ]
            if page.changes_to_release_date
            else [],
        }
        return release_fields

    def _construct_message_for_delete(self, page):
        """Build a dict that matches the 'content-deleted' schema:
        - required: uri
        - optional: trace_id.
        """
        message = {
            "uri": page.url_path,
        }

        if hasattr(page, "trace_id"):
            message["trace_id"] = page.trace_id

        return message

    def _map_page_type_to_content_type(self, page):
        """Maps the class name of a given page object to a corresponding content type string."""
        page_class_name = page.__class__.__name__

        mapping = {
            "ReleaseCalendarPage": "release",
            "StatisticalArticlePage": "bulletin",
            "InformationPage": "static_page",
            "IndexPage": "static_landing_page",
            "MethodologyPage": "static_methodology",
        }

        return mapping.get(page_class_name)


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
