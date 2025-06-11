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

    kafka_settings: list[tuple[str, str, str]] = [
        ("KAFKA_SERVERS", "localhost:9092", "search.E001"),
    ]

    for setting, hint_value, missing_id in kafka_settings:
        # Checking if not value catches None, empty string, 0, False, etc.
        value = getattr(settings, setting, None)
        if not value:
            errors.append(
                Error(
                    f"{setting} is missing or empty.",
                    hint=f"Set {setting} to e.g. '{hint_value}'.",
                    id=missing_id,
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

    for model in get_page_models():
        # Skip anything that appears in the exclusion list by class name
        if model.__name__ in excluded_types:
            continue

        if not getattr(model, "search_index_content_type", None):
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
