import logging
from abc import ABC, abstractmethod
from functools import cache
from typing import TYPE_CHECKING

from django.conf import settings

from cms.search.utils import build_page_uri, build_resource_dict

logger = logging.getLogger(__name__)


if TYPE_CHECKING:
    from wagtail.models import Page


@cache
def get_publisher() -> BasePublisher:
    """Return the configured publisher backend."""
    if settings.SEARCH_INDEX_PUBLISHER_BACKEND == "kafka":
        # Lazily load the kafka publisher
        from .kafka import KafkaPublisher  # pylint: disable=import-outside-toplevel, cyclic-import

        return KafkaPublisher()
    return LogPublisher()


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
        self._publish(self.CREATED_OR_UPDATED_CHANNEL, build_resource_dict(page, old_url_path=old_url_path))

    def publish_deleted(self, page: Page) -> None:
        """Build the message for the deleted event.
        Delegate sending to the subclass's _publish().
        """
        self._publish(
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


class LogPublisher(BasePublisher):
    """Publishes 'messages' by simply logging them (no real message bus)."""

    def _publish(self, channel: str | None, message: dict) -> None:
        """Log the message."""
        logger.info("LogPublisher: Publishing to channel=%s, message=%s", channel, message)
