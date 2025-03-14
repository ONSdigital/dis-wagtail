from django.conf import settings

from .publishers import KafkaPublisher, LogPublisher


def get_publisher():
    backend = settings.PUBLISHER_BACKEND
    if backend == "kafka":
        return KafkaPublisher()
    return LogPublisher()
