from django.conf import settings

from .publishers import KafkaPublisher, LogPublisher, NullPublisher


def get_publisher():
    backend = settings.PUBLISHER_BACKEND
    if backend == "kafka":
        return KafkaPublisher()
    elif backend == "log":
        return LogPublisher()
    else:
        return NullPublisher()
