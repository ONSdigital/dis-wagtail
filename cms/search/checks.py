from collections.abc import Iterable
from typing import Any, Optional

from django.apps import AppConfig
from django.conf import settings
from django.core.checks import Error, register


@register()
def check_kafka_settings(app_configs: Optional[Iterable[AppConfig]], **kwargs: Any) -> list[Error]:  # pylint: disable=unused-argument
    """Check that required Kafka settings are present."""
    errors: list[Error] = []

    # Only run checks if the provider is set to "kafka"
    if getattr(settings, "SEARCH_INDEX_PUBLISHER_BACKEND", "") != "kafka":
        return errors

    kafka_settings: list[tuple[str, str, str, str]] = [
        ("KAFKA_SERVER", "localhost:9092", "search.E001", "search.E002"),
        (
            "KAFKA_CHANNEL_CREATED_OR_UPDATED",
            "the Kafka topic you use for content updates",
            "search.E003",
            "search.E004",
        ),
        (
            "KAFKA_CHANNEL_DELETED",
            "the Kafka topic you use for content deletions",
            "search.E005",
            "search.E006",
        ),
    ]

    for setting, hint_value, missing_id, empty_id in kafka_settings:
        if not hasattr(settings, setting):
            errors.append(
                Error(
                    f"Missing required setting {setting}",
                    hint=f"Add {setting} to your Django settings.",
                    id=missing_id,
                )
            )
        elif not getattr(settings, setting):
            errors.append(
                Error(
                    f"{setting} setting is empty.",
                    hint=f"Set {setting} to e.g. '{hint_value}'.",
                    id=empty_id,
                )
            )

    return errors
