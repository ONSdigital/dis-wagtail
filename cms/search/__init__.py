from django.conf import settings

from .publishers import KafkaPublisher, LogPublisher, NullPublisher


def get_publisher():
    backend = settings.PUBLISHER_BACKEND
    if backend == "kafka":
        return KafkaPublisher()
    if backend == "log":
        return LogPublisher()
    return NullPublisher()
