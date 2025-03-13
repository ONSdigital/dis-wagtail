import json
import logging
from abc import ABC, abstractmethod

from django.conf import settings
from kafka import KafkaProducer

logger = logging.getLogger(__name__)


class BasePublisher(ABC):
    """BasePublisher defines shared functionalities, such as how to build a message
    for created/updated or deleted events. Each subclass only needs to define how
    to actually publish (i.e., send) the built message.
    """

    def publish_created_or_updated(self, page):
        """Build the message for the created/updated event.
        Delegate sending to the subclass's _publish_to_service().
        """
        topic = self.get_topic_created_or_updated()
        message = self._construct_message_for_create_update(page)
        logger.info(
            "BasePublisher: About to publish created/updated message=%s to topic=%s",
            message,
            topic,
        )
        return self._publish_to_service(topic, message)

    def publish_deleted(self, page):
        """Build the message for the deleted event.
        Delegate sending to the subclass's _publish_to_service().
        """
        topic = self.get_topic_deleted()
        message = self._construct_message_for_delete(page)
        logger.info(
            "BasePublisher: About to publish deleted message=%s to topic=%s",
            message,
            topic,
        )
        return self._publish_to_service(topic, message)

    @abstractmethod
    def _publish_to_service(self, topic, message):
        """Each child class defines how to actually send/publish
        the message (e.g., Kafka, logging, etc.).
        """
        pass

    @abstractmethod
    def get_topic_created_or_updated(self):
        """Provide the topic (or other necessary routing key) for created/updated.
        This can be a no-op or empty string for some implementations.
        """
        pass

    @abstractmethod
    def get_topic_deleted(self):
        """Provide the topic (or other necessary routing key) for deleted messages.
        This can be a no-op or empty string for some implementations.
        """
        pass

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
            "release_date": (
                page.release_date.isoformat().replace("+00:00", "Z")
                if content_type == "release" and getattr(page, "release_date", None)
                else None
            ),
            "summary": page.summary,
            "title": page.title,
            "topics": list(page.topics.values_list("topic_id", flat=True)) if hasattr(page, "topics") else [],
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
            "date_changes": [],
        }

        # If page.changes_to_release_date exists, add the first item's reason & previous date
        if hasattr(page, "changes_to_release_date") and page.changes_to_release_date:
            first_change = page.changes_to_release_date[0].value
            release_fields["date_changes"].append(
                {
                    "change_notice": first_change.get("reason_for_change"),
                    "previous_date": str(first_change.get("previous_date").isoformat().replace("+00:00", "Z"))
                    if first_change.get("previous_date")
                    else None,
                }
            )
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


class KafkaPublisher(BasePublisher):
    """Publishes messages to Kafka for 'search-content-updated' (created or updated)
    and 'search-content-deleted' (deleted) events, aligning with the StandardPayload
    / ReleasePayload / content-deleted schema definitions.
    """

    def __init__(self):
        # Read Kafka configs settings
        self.kafka_server = settings.KAFKA_SERVER
        self._topic_created_or_updated = settings.KAFKA_TOPIC_CREATED_OR_UPDATED
        self._topic_deleted = settings.KAFKA_TOPIC_DELETED

        self.producer = KafkaProducer(
            bootstrap_servers=[self.kafka_server],
            api_version=(3, 8, 0),
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
        )

    def get_topic_created_or_updated(self):
        return self._topic_created_or_updated

    def get_topic_deleted(self):
        return self._topic_deleted

    def _publish_to_service(self, topic, message):
        """Send the message to Kafka."""
        logger.info("KafkaPublisher: Publishing to topic=%s, message=%s", topic, message)
        future = self.producer.send(topic, message)
        # Optionally block for the result, capturing metadata or error
        result = future.get(timeout=10)  # Wait up to 10s for send to complete
        logger.info("KafkaPublisher: Publish result for topic %s: %s", topic, result)
        return result


class LogPublisher(BasePublisher):
    """Publishes 'messages' by simply logging them (no real message bus)."""

    def get_topic_created_or_updated(self):
        return "log-created-or-updated"

    def get_topic_deleted(self):
        return "log-deleted"

    def _publish_to_service(self, topic, message):
        logger.info("LogPublisher: topic=%s message=%s", topic, message)


class NullPublisher(BasePublisher):
    """Publisher that does nothing—no logs, no sends—used to disable publishing entirely."""

    def get_topic_created_or_updated(self):
        pass

    def get_topic_deleted(self):
        pass

    def _publish_to_service(self, topic, message):
        pass
