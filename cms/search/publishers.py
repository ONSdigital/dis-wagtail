import json
import logging
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from django.conf import settings
from kafka import KafkaProducer

from cms.search.utils.resource_builders import build_resource_dict

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
        channel = self.created_or_updated_channel
        message = build_resource_dict(page)
        return self._publish(channel, message)

    def publish_deleted(self, page: "Page") -> None:
        """Build the message for the deleted event.
        Delegate sending to the subclass's _publish().
        """
        channel = self.deleted_channel
        message = {
            "uri": page.url_path,
        }
        return self._publish(channel, message)

    @abstractmethod
    def _publish(self, channel: str | None, message: dict) -> None:
        """Each child class defines how to actually send/publish
        the message (e.g., Kafka, logging, etc.).
        """

    @property
    @abstractmethod
    def created_or_updated_channel(self) -> str | None:
        """Provide the channel (or other necessary routing key) for created/updated.
        This can be a no-op or empty string for some implementations.
        """

    @property
    @abstractmethod
    def deleted_channel(self) -> str | None:
        """Provide the channel (or other necessary routing key) for deleted messages.
        This can be a no-op or empty string for some implementations.
        """


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
        self.producer = KafkaProducer(
            bootstrap_servers=[settings.KAFKA_SERVER],
            api_version=settings.KAFKA_API_VERSION,
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
            retries=5,
        )

    @property
    def created_or_updated_channel(self) -> str | None:
        return settings.KAFKA_CHANNEL_CREATED_OR_UPDATED

    @property
    def deleted_channel(self) -> str | None:
        return settings.KAFKA_CHANNEL_DELETED

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

    @property
    def created_or_updated_channel(self) -> str:
        return "log-created-or-updated"

    @property
    def deleted_channel(self) -> str:
        return "log-deleted"

    def _publish(self, channel: str | None, message: dict) -> None:
        """Log the message."""
        logger.info("LogPublisher: Publishing to channel=%s, message=%s", channel, message)
