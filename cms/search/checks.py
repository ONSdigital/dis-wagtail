from collections.abc import Iterable
from typing import TYPE_CHECKING, Any

from django.conf import settings
from django.core.checks import Error, register
from wagtail.models import get_page_models

if TYPE_CHECKING:
    from django.apps import AppConfig


@register()
def check_kafka_settings(app_configs: Iterable["AppConfig"] | None, **kwargs: Any) -> list[Error]:  # pylint: disable=unused-argument
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
def check_search_index_content_type(app_configs: Iterable["AppConfig"] | None, **kwargs: Any) -> list[Error]:  # pylint: disable=unused-argument
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
                    id="search.E002",
                )
            )

    return errors


@register()
def check_search_index_included_languages(app_configs: Iterable["AppConfig"] | None, **kwargs: Any) -> list[Error]:  # pylint: disable=unused-argument
    """Validate SEARCH_INDEX_INCLUDED_LANGUAGES configuration.

    - Must not be empty
    - Must contain only codes declared in LANGUAGES/WAGTAIL_CONTENT_LANGUAGES
    - Must be normalised to lowercase
    """
    errors: list[Error] = []

    included = getattr(settings, "SEARCH_INDEX_INCLUDED_LANGUAGES", [])

    # Ensure it's a non-empty iterable of strings
    if not included or not all(isinstance(c, str) for c in included):
        errors.append(
            Error(
                "SEARCH_INDEX_INCLUDED_LANGUAGES must be a non-empty list of language codes.",
                hint=(
                    "Set SEARCH_INDEX_INCLUDED_LANGUAGES to a comma-separated env value (e.g. 'en-gb,cy') "
                    "or ensure LANGUAGE_CODE is valid; see cms.settings.base.LANGUAGES."
                ),
                id="search.E003",
            )
        )
        return errors

    # Valid codes from LANGUAGES (tuple of (code, name))
    valid_codes = {code for code, _ in getattr(settings, "LANGUAGES", [])}

    # Check membership
    invalid_codes: list[str] = []

    for code in included:
        if code not in valid_codes:
            invalid_codes.append(code)

    if invalid_codes:
        errors.append(
            Error(
                "SEARCH_INDEX_INCLUDED_LANGUAGES contains codes not present in LANGUAGES.",
                hint=(
                    f"Remove or correct invalid codes: {', '.join(sorted(invalid_codes))}. "
                    f"Valid codes: {', '.join(sorted(valid_codes))}."
                ),
                id="search.E004",
            )
        )

    return errors
