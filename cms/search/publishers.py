import json
import logging
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, cast

from aws_msk_iam_sasl_signer import MSKAuthTokenProvider
from django.conf import settings
from kafka import KafkaProducer
from kafka.sasl.oauth import AbstractTokenProvider

from cms.core.cache import memory_cache
from cms.search.utils import build_page_uri, build_resource_dict

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

    CREATED_OR_UPDATED_CHANNEL = "search-content-updated"
    DELETED_CHANNEL = "search-content-deleted"

    def publish_created_or_updated(self, page: Page, old_url_path: str | None = None) -> None:
        """Build the message for the created/updated event.
        Delegate sending to the subclass's _publish().
        """
        return self._publish(self.CREATED_OR_UPDATED_CHANNEL, build_resource_dict(page, old_url_path=old_url_path))

    def publish_deleted(self, page: Page) -> None:
        """Build the message for the deleted event.
        Delegate sending to the subclass's _publish().
        """
        return self._publish(
            self.DELETED_CHANNEL,
            {
                "uri": build_page_uri(page),
            },
        )

    @abstractmethod
    def _publish(self, channel: str | None, message: dict) -> None:
        """Each child class defines how to actually send/publish
        the message (e.g., Kafka, logging, etc.).
        """


class IAMKafkaTokenProvider(AbstractTokenProvider):
    """A token provider which uses IAM to request an auth token."""

    # Generating the token does a request, so cache it for slightly less than the expiration.
    @memory_cache(
        MSKAuthTokenProvider.DEFAULT_TOKEN_EXPIRY_SECONDS - 5,
        key_generator_callable=lambda self: f"{__name__}.{type(self).__qualname__}",
    )
    def token(self) -> str:
        token, _ = MSKAuthTokenProvider.generate_auth_token(settings.AWS_REGION)
        return cast(str, token)


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
        if settings.KAFKA_USE_IAM_AUTH:
            auth_config = {
                "security_protocol": "SASL_SSL",
                "sasl_mechanism": "OAUTHBEARER",
                "sasl_oauth_token_provider": IAMKafkaTokenProvider(),
            }
        else:
            auth_config = {}

        self.producer = KafkaProducer(
            bootstrap_servers=settings.KAFKA_SERVERS,
            api_version_auto_timeout_ms=5000,
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
            retries=5,
            **auth_config,
        )

    def _publish(self, channel: str | None, message: dict) -> RecordMetadata:
        """Send the message to Kafka."""
        logger.info("KafkaPublisher: Publishing to channel=%s, message=%s", channel, message)
        future = self.producer.send(channel, message)
        # Wait for the send to complete and get the result
        result = future.get(timeout=10)  # Wait up to 10s for send to complete
        logger.info("KafkaPublisher: Publish result for channel %s: %s", channel, result)
        return result


class LogPublisher(BasePublisher):
    """Publishes 'messages' by simply logging them (no real message bus)."""

    def _publish(self, channel: str | None, message: dict) -> None:
        """Log the message."""
        logger.info("LogPublisher: Publishing to channel=%s, message=%s", channel, message)
