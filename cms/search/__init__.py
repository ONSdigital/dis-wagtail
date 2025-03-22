from typing import Union

from django.conf import settings

from .publishers import KafkaPublisher, LogPublisher


def get_publisher() -> Union[KafkaPublisher, LogPublisher]:
    """Return the configured publisher backend."""
    backend = settings.PUBLISHER_BACKEND
    if backend == "kafka":
        return KafkaPublisher()
    return LogPublisher()
