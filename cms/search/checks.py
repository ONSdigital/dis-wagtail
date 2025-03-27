from collections.abc import Iterable
from typing import Any, Optional

from django.apps import AppConfig
from django.conf import settings
from django.core.checks import Error, register
from wagtail.models import get_page_models


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
        else:
            value = getattr(settings, setting)
            if value is None or value == "":
                errors.append(
                    Error(
                        f"{setting} setting is empty.",
                        hint=f"Set {setting} to e.g. '{hint_value}'.",
                        id=empty_id,
                    )
                )

    return errors


@register()
def check_search_index_content_type(app_configs: Optional[Iterable[AppConfig]], **kwargs: Any) -> list[Error]:  # pylint: disable=unused-argument
    """Check that each page model not excluded by SEARCH_INDEX_EXCLUDED_PAGE_TYPES
    defines a 'search_index_content_type' attribute/property.
    """
    errors: list[Error] = []

    # Fetch the excluded list (defaulting to empty tuple if not set)
    excluded_types = getattr(settings, "SEARCH_INDEX_EXCLUDED_PAGE_TYPES", ())

    # Get all Wagtail Page subclasses
    page_models = get_page_models()

    for model in page_models:
        # Skip anything that appears in the exclusion list by class name
        if model.__name__ in excluded_types:
            continue

        if not hasattr(model, "search_index_content_type"):
            errors.append(
                Error(
                    f"Page model '{model.__name__}' is not in SEARCH_INDEX_EXCLUDED_PAGE_TYPES "
                    f"but does not define a 'search_index_content_type'.",
                    hint=(
                        "Either add an attribute/property 'search_index_content_type' to "
                        f"'{model.__name__}' or add '{model.__name__}' to "
                        "SEARCH_INDEX_EXCLUDED_PAGE_TYPES."
                    ),
                    id="search.E007",
                )
            )

    return errors
