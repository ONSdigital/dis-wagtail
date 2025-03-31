import json
import logging
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Optional

from django.conf import settings
from django.utils.encoding import force_str
from kafka import KafkaProducer
from wagtail.rich_text import get_text_for_indexing

logger = logging.getLogger(__name__)


if TYPE_CHECKING:
    from kafka.producer.future import RecordMetadata
    from wagtail.models import Page


class BasePublisher(ABC):
    """BasePublisher defines shared functionalities, such as how to build a message
    for created/updated or deleted events. Each subclass only needs to define how
    to actually publish (i.e., send) the built message.

    dp-search-data-extractor spec link:
    https://github.com/ONSdigital/dp-search-data-extractor/blob/develop/specification.yml#L53
    dp-search-data-importer spec link:
    https://github.com/ONSdigital/dp-search-data-importer/blob/30fb507e90f2cf1974ec0ca43bb0466307e2f112/specification.yml#L186
    contract: https://github.com/ONSdigital/dis-search-upstream-stub/blob/main/docs/contract/resource_metadata.yml
    """

    def publish_created_or_updated(self, page: "Page") -> None:
        """Build the message for the created/updated event.
        Delegate sending to the subclass's _publish().
        """
        channel = self.get_created_or_updated_channel()
        message = self._construct_message_for_create_update(page)
        return self._publish(channel, message)

    def publish_deleted(self, page: "Page") -> None:
        """Build the message for the deleted event.
        Delegate sending to the subclass's _publish().
        """
        channel = self.get_deleted_channel()
        message = {
            "uri": page.url_path,
        }
        return self._publish(channel, message)

    @abstractmethod
    def _publish(self, channel: str | None, message: dict) -> None:
        """Each child class defines how to actually send/publish
        the message (e.g., Kafka, logging, etc.).
        """

    @abstractmethod
    def get_created_or_updated_channel(self) -> str | None:
        """Provide the channel (or other necessary routing key) for created/updated.
        This can be a no-op or empty string for some implementations.
        """

    @abstractmethod
    def get_deleted_channel(self) -> str | None:
        """Provide the channel (or other necessary routing key) for deleted messages.
        This can be a no-op or empty string for some implementations.
        """

    def _construct_message_for_create_update(self, page: "Page") -> dict:
        """Build a dict that matches the agreed metadata schema for 'created/updated'.

        resource_metadata.yml:
           - StandardPayload: requires {uri, title, content_type}, optional fields
           - ReleasePayload: extends StandardPayload with release-specific fields
        """
        # Common fields for StandardPayload (also part of ReleasePayload)
        # The schema requires at minimum: uri, title, content_type
        message = {
            "uri": page.url_path,
            "content_type": page.search_index_content_type,
            "release_date": (
                page.release_date.isoformat()
                if page.search_index_content_type == "release" and getattr(page, "release_date", None)
                else None
            ),
            "summary": get_text_for_indexing(force_str(page.summary)),
            "title": page.title,
            "topics": getattr(page, "topic_ids", []),
        }

        # If it's a Release, we add the extra fields from ReleasePayload
        if page.search_index_content_type == "release":
            message.update(self._construct_release_specific_fields(page))
        return message

    def _construct_release_specific_fields(self, page: "Page") -> dict:
        """Constructs and returns a dictionary with release-specific fields."""
        release_fields = {
            "finalised": page.status in ["CONFIRMED", "PROVISIONAL"],
            "cancelled": page.status == "CANCELLED",
            "published": page.status == "PUBLISHED",
            "date_changes": [],
        }

        if getattr(page, "changes_to_release_date", None):
            release_fields["date_changes"] = [
                {
                    "change_notice": change.value.get("reason_for_change"),
                    "previous_date": change.value.get("previous_date").isoformat(),
                }
                for change in page.changes_to_release_date
            ]
        return release_fields


class KafkaPublisher(BasePublisher):
    """Publishes messages to Kafka for 'search-content-updated' (created or updated)
    and 'search-content-deleted' (deleted) events, aligning with the StandardPayload
    / ReleasePayload / content-deleted schema definitions.

    dp-search-data-extractor spec link:
    https://github.com/ONSdigital/dp-search-data-extractor/blob/develop/specification.yml#L53
    dp-search-data-importer spec link:
    https://github.com/ONSdigital/dp-search-data-importer/blob/30fb507e90f2cf1974ec0ca43bb0466307e2f112/specification.yml#L186
    contract: https://github.com/ONSdigital/dis-search-upstream-stub/blob/main/docs/contract/resource_metadata.yml
    """

    def __init__(self) -> None:
        # Read Kafka configs settings
        self.kafka_server = settings.KAFKA_SERVER
        self.kafka_api_version = settings.KAFKA_API_VERSION
        self._channel_created_or_updated: Optional[str] = settings.KAFKA_CHANNEL_CREATED_OR_UPDATED
        self._channel_deleted: Optional[str] = settings.KAFKA_CHANNEL_DELETED

        self.producer = KafkaProducer(
            bootstrap_servers=[self.kafka_server],
            api_version=self.kafka_api_version,
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
        )

    def get_created_or_updated_channel(self) -> str | None:
        return self._channel_created_or_updated

    def get_deleted_channel(self) -> str | None:
        return self._channel_deleted

    def _publish(self, channel: str | None, message: dict) -> "RecordMetadata":
        """Send the message to Kafka."""
        logger.info("KafkaPublisher: Publishing to channel=%s, message=%s", channel, message)
        future = self.producer.send(channel, message)
        # Optionally block for the result, capturing metadata or error
        result = future.get(timeout=10)  # Wait up to 10s for send to complete
        logger.info("KafkaPublisher: Publish result for channel %s: %s", channel, result)
        return result


class LogPublisher(BasePublisher):
    """Publishes 'messages' by simply logging them (no real message bus)."""

    def get_created_or_updated_channel(self) -> str:
        return "log-created-or-updated"

    def get_deleted_channel(self) -> str:
        return "log-deleted"

    def _publish(self, channel: str | None, message: dict) -> None:
        """Log the message."""
        logger.info("LogPublisher: Publishing to channel=%s, message=%s", channel, message)
