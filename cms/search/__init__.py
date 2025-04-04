from functools import cache

from django.conf import settings

from .publishers import KafkaPublisher, LogPublisher


@cache
def get_publisher() -> KafkaPublisher | LogPublisher:
    """Return the configured publisher backend."""
    backend = settings.SEARCH_INDEX_PUBLISHER_BACKEND
    if backend == "kafka":
        return KafkaPublisher()
    return LogPublisher()
